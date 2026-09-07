"""账号 / 令牌 / 训练记录的本地文件存储。

设计约定：
- 纯标准库（hashlib + secrets），不引入数据库依赖；
- 密码使用 PBKDF2-HMAC-SHA256 加盐哈希，绝不存明文；
- 令牌保存在内存（服务重启后需重新登录），不回写磁盘；
- 所有读写经一把 RLock 串行化，保证 FastAPI 多线程下安全。
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

_ACCOUNTS_DIR = Path(__file__).resolve().parent
USERS_FILE = _ACCOUNTS_DIR / "users.json"
RECORDS_FILE = _ACCOUNTS_DIR / "training_records.json"

ROLES = ("admin", "staff", "student")
PBKDF2_ITERATIONS = 200_000

# 首次启动自动创建的演示账号（admin / staff / student）
DEFAULT_ACCOUNTS: list[dict[str, str]] = [
    {"username": "admin", "password": "admin123", "display_name": "系统管理员", "role": "admin"},
    {"username": "staff", "password": "staff123", "display_name": "带教老师", "role": "staff"},
    {"username": "student", "password": "student123", "display_name": "演示学生", "role": "student"},
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return dk.hex(), salt


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


class AccountStore:
    """线程安全的本地账号 / 训练记录存储。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: dict[str, dict[str, Any]] = {}
        self._tokens: dict[str, str] = {}  # token -> username
        self._records: list[dict[str, Any]] = []
        self._load()
        self._seed_default_accounts()

    # ── 持久化 ─────────────────────────────────────────
    def _load(self) -> None:
        users = _load_json(USERS_FILE)
        if isinstance(users, dict):
            self._users = users
        records = _load_json(RECORDS_FILE)
        if isinstance(records, list):
            self._records = records

    def _flush_users(self) -> None:
        _save_json(USERS_FILE, self._users)

    def _flush_records(self) -> None:
        _save_json(RECORDS_FILE, self._records)

    def _seed_default_accounts(self) -> None:
        changed = False
        for acc in DEFAULT_ACCOUNTS:
            if acc["username"] in self._users:
                continue
            pwhash, salt = hash_password(acc["password"])
            self._users[acc["username"]] = {
                "username": acc["username"],
                "display_name": acc["display_name"],
                "role": acc["role"],
                "password_hash": pwhash,
                "salt": salt,
                "created_at": _now(),
                "disabled": False,
            }
            changed = True
        if changed:
            self._flush_users()

    # ── 用户 ───────────────────────────────────────────
    def register(
        self,
        username: str,
        password: str,
        display_name: str = "",
        *,
        role: str = "student",
    ) -> dict[str, Any]:
        """注册新用户，默认角色为 student。失败抛 ValueError。"""
        with self._lock:
            username = username.strip()
            if len(username) < 3:
                raise ValueError("用户名至少 3 个字符")
            if len(password) < 6:
                raise ValueError("密码至少 6 位")
            if username in self._users:
                raise ValueError("用户名已存在")
            if role not in ROLES:
                raise ValueError(f"非法角色: {role}")
            pwhash, salt = hash_password(password)
            user: dict[str, Any] = {
                "username": username,
                "display_name": (display_name or username).strip(),
                "role": role,
                "password_hash": pwhash,
                "salt": salt,
                "created_at": _now(),
                "disabled": False,
            }
            self._users[username] = user
            self._flush_users()
            return self._public_user(user)

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._users.get(username.strip())
            if not user or user.get("disabled"):
                return None
            pwhash, _ = hash_password(password, user.get("salt", ""))
            if not secrets.compare_digest(pwhash, user.get("password_hash", "")):
                return None
            return self._public_user(user)

    def create_token(self, username: str) -> str:
        with self._lock:
            token = secrets.token_hex(32)
            self._tokens[token] = username
            return token

    def user_by_token(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            username = self._tokens.get(token)
            if not username:
                return None
            user = self._users.get(username)
            if not user or user.get("disabled"):
                return None
            return self._public_user(user)

    def revoke_token(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._users.get(username)
            return self._public_user(user) if user else None

    def list_users(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                self._public_user(u)
                for u in sorted(self._users.values(), key=lambda x: x["created_at"])
            ]

    def set_user_role(self, username: str, role: str) -> dict[str, Any]:
        with self._lock:
            user = self._users.get(username)
            if not user:
                raise ValueError(f"用户不存在: {username}")
            if role not in ROLES:
                raise ValueError(f"非法角色: {role}")
            if username == "admin" and role != "admin":
                raise ValueError("内置管理员账号不可降级")
            user["role"] = role
            self._flush_users()
            return self._public_user(user)

    def set_user_disabled(self, username: str, disabled: bool) -> dict[str, Any]:
        with self._lock:
            user = self._users.get(username)
            if not user:
                raise ValueError(f"用户不存在: {username}")
            if username == "admin" and disabled:
                raise ValueError("内置管理员账号不可禁用")
            user["disabled"] = bool(disabled)
            self._flush_users()
            return self._public_user(user)

    def delete_user(self, username: str) -> None:
        with self._lock:
            if username == "admin":
                raise ValueError("内置管理员账号不可删除")
            self._users.pop(username, None)
            self._flush_users()

    @staticmethod
    def _public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "role": user.get("role", "student"),
            "created_at": user.get("created_at", ""),
            "disabled": bool(user.get("disabled", False)),
        }

    # ── 训练记录 ───────────────────────────────────────
    def add_training_record(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            rec = {
                "id": secrets.token_hex(8),
                "created_at": _now(),
                **record,
            }
            self._records.append(rec)
            self._flush_records()
            return rec

    def records_for(self, username: str) -> list[dict[str, Any]]:
        with self._lock:
            return [r for r in self._records if r.get("username") == username]

    def all_records(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._records[-limit:]))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_users = len(self._users)
            by_role: dict[str, int] = {}
            for u in self._users.values():
                role = u.get("role", "student")
                by_role[role] = by_role.get(role, 0) + 1
            scores = [r.get("overall_score") for r in self._records if isinstance(r.get("overall_score"), (int, float))]
            by_study: dict[str, int] = {}
            for r in self._records:
                study = r.get("study") or "未知"
                by_study[study] = by_study.get(study, 0) + 1
            return {
                "total_users": total_users,
                "by_role": by_role,
                "total_records": len(self._records),
                "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
                "pass_rate": (
                    round(
                        100.0 * sum(1 for r in self._records if r.get("passed"))
                        / len(self._records),
                        1,
                    )
                    if self._records
                    else None
                ),
                "by_study": by_study,
            }


store = AccountStore()
