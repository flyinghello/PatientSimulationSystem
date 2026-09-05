"""火山方舟 — 入组前患者顾虑池生成 Agent。

技能说明：
  service/skills/concern_pool.md

输入：
  - 研究背景 JSON（experiment_background 产出）
  - CRC 培训材料 Markdown（如 crc_interview.md）

输出：
  service/acknowledge/questions_pool/*.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-character-251128"
DEFAULT_TEMPERATURE = 0.4
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 120.0
DEFAULT_TOPIC_MIN = 10
DEFAULT_TOPIC_MAX = 15

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_SKILL_PATH = _SERVICE_ROOT / "skills" / "concern_pool.md"
_DEFAULT_BACKGROUND = (
    _SERVICE_ROOT
    / "acknowledge"
    / "relative_experiment"
    / "B-cell malignancies.background.json"
)
_DEFAULT_TRAINING = _SERVICE_ROOT / "acknowledge" / "crc_interview.md"
_DEFAULT_OUT_DIR = _SERVICE_ROOT / "acknowledge" / "questions_pool"

ITEM_KEYS = ("话题", "顾虑", "触发情境", "示例问法", "训练目标")

OUTPUT_SCHEMA_EXAMPLE = [
    {
        "话题": "到院安排",
        "顾虑": "担心经常来医院影响工作",
        "触发情境": "患者请假困难，或CRC介绍给药及到院安排",
        "示例问法": [
            "参加以后需要经常来医院吗？",
            "24周打一针，是不是中间不用来了？",
        ],
        "训练目标": "解释安排，了解患者时间限制",
    },
    {
        "话题": "安慰剂分组",
        "顾虑": "担心分不到研究药",
        "触发情境": "患者听到随机分组或安慰剂",
        "示例问法": ["我能自己选用研究药吗？"],
        "训练目标": "用通俗语言解释分组方式",
    },
]


# ---------------------------------------------------------------------------
# Config / data
# ---------------------------------------------------------------------------
@dataclass
class ConcernPoolConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT
    skill_path: Path = _SKILL_PATH
    trust_env: bool = True
    topic_min: int = DEFAULT_TOPIC_MIN
    topic_max: int = DEFAULT_TOPIC_MAX

    @classmethod
    def from_env(cls, **overrides: Any) -> ConcernPoolConfig:
        try:
            from config import setting as cfg
        except ImportError:  # pragma: no cover
            cfg = None

        def _get(*keys: str, default: str = "") -> str:
            for key in keys:
                val = os.getenv(key)
                if val and val.strip():
                    return val.strip()
            if cfg is not None:
                for key in keys:
                    mapped = {
                        "TEXT_GENERATION_API_KEY": "ARK_API_KEY",
                        "ARK_API_KEY": "ARK_API_KEY",
                        "TEXT_GENERATION_MODEL": "ARK_MODEL",
                        "ARK_MODEL": "ARK_MODEL",
                        "ARK_BASE_URL": "ARK_BASE_URL",
                    }.get(key, key)
                    val = getattr(cfg, mapped, None)
                    if val and str(val).strip():
                        return str(val).strip()
            return default

        skill = overrides.pop("skill_path", None)
        no_proxy = os.getenv("ARK_NO_PROXY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        values: dict[str, Any] = {
            "api_key": _get(
                "TEXT_GENERATION_API_KEY",
                "ARK_API_KEY",
                "VOLC_ARK_API_KEY",
            ),
            "base_url": _get("ARK_BASE_URL", default=DEFAULT_BASE_URL).rstrip("/"),
            "model": _get(
                "TEXT_GENERATION_MODEL",
                "ARK_MODEL",
                default=DEFAULT_MODEL,
            ),
            "temperature": float(
                os.getenv("ARK_CONCERN_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "max_tokens": int(
                os.getenv("ARK_CONCERN_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
            ),
            "timeout": float(os.getenv("ARK_TIMEOUT", str(DEFAULT_TIMEOUT))),
            "trust_env": not no_proxy,
            "topic_min": int(os.getenv("ARK_CONCERN_TOPIC_MIN", str(DEFAULT_TOPIC_MIN))),
            "topic_max": int(os.getenv("ARK_CONCERN_TOPIC_MAX", str(DEFAULT_TOPIC_MAX))),
        }
        if skill is not None:
            values["skill_path"] = Path(skill)
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def require_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "缺少鉴权信息：请在项目根目录 .env 中设置 TEXT_GENERATION_API_KEY"
            )


@dataclass
class ConcernItem:
    话题: str = ""
    顾虑: str = ""
    触发情境: str = ""
    示例问法: list[str] = field(default_factory=list)
    训练目标: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in ITEM_KEYS}


@dataclass
class ConcernPoolResult:
    items: list[ConcernItem] = field(default_factory=list)
    raw_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_list(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.items]


# ---------------------------------------------------------------------------
# IO / prompt
# ---------------------------------------------------------------------------
def load_skill(path: Path | None = None) -> str:
    p = path or _SKILL_PATH
    if not p.is_file():
        raise FileNotFoundError(f"技能说明文件不存在: {p}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"技能说明文件为空: {p}")
    return text


def load_text(path: Path | str) -> str:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在: {p}")
    return p.read_text(encoding="utf-8")


def load_background(path: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path, dict):
        return path
    p = Path(path)
    data = json.loads(load_text(p))
    if not isinstance(data, dict):
        raise ValueError(f"研究背景 JSON 根节点必须是对象: {p}")
    return data


def default_output_path(background_path: Path, out_dir: Path) -> Path:
    stem = background_path.stem
    if stem.endswith(".background"):
        stem = stem[: -len(".background")]
    return out_dir / f"{stem}.concerns.json"


def build_system_prompt(
    skill: str,
    *,
    topic_min: int = DEFAULT_TOPIC_MIN,
    topic_max: int = DEFAULT_TOPIC_MAX,
) -> str:
    schema_text = json.dumps(OUTPUT_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return (
        "你是 CRC 沟通训练内容设计师，负责生成入组前患者顾虑池。\n"
        "请严格依据下方技能说明，结合用户给出的研究背景与培训材料输出 JSON。\n\n"
        "【技能说明】\n"
        f"{skill.strip()}\n\n"
        "【任务提示词】\n"
        "根据研究背景和培训资料，生成入组前患者顾虑池。\n\n"
        "要求：\n"
        "1. 提取患者可能表达的疑问、顾虑。\n"
        "2. 多项目协调、研究者签字、CRC私活等内容暂不纳入。\n"
        "3. 入组后事件可改为入组前对未来的担忧。\n"
        "4. 相同顾虑合并，一个话题可以有多个示例问法。\n"
        f"5. 先生成{topic_min}—{topic_max}个话题，不需要复杂分类。\n"
        "6. 提取训练目标，不将培训材料中的回答直接当成标准答案。\n"
        "7. 不编造研究事实。\n\n"
        "【输出 Schema 示例】\n"
        f"{schema_text}\n\n"
        "只输出一个 JSON 数组，字段名与示例完全一致；不要 markdown 代码块，不要其它说明。"
    )


def build_user_prompt(*, background: dict[str, Any], training_material: str) -> str:
    bg = json.dumps(background, ensure_ascii=False, indent=2)
    training = training_material.strip()
    if len(training) > 12000:
        training = training[:12000] + "\n…（已截断）"
    return (
        "请根据以下材料生成入组前患者顾虑池 JSON 数组。\n\n"
        "【研究背景】\n"
        f"{bg}\n\n"
        "【培训材料】\n"
        f"{training}"
    )


_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def parse_concern_pool_json(text: str) -> list[dict[str, Any]]:
    raw = text.strip()
    if not raw:
        raise ValueError("模型返回为空，无法解析顾虑池")

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    match = _JSON_ARRAY_RE.search(raw)
    if match:
        candidates.insert(0, match.group(0))

    last_err: Exception | None = None
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("items", "concerns", "顾虑池", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
    raise ValueError(f"无法解析顾虑池 JSON: {last_err}; 原文前 200 字={raw[:200]!r}")


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_concern_pool(
    items: list[dict[str, Any]],
    *,
    topic_min: int = DEFAULT_TOPIC_MIN,
    topic_max: int = DEFAULT_TOPIC_MAX,
    raw_text: str = "",
    raw: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> ConcernPoolResult:
    out: list[ConcernItem] = []
    seen_topics: set[str] = set()

    for item in items:
        topic = str(item.get("话题", "") or "").strip()
        concern = str(item.get("顾虑", "") or "").strip()
        if not topic or not concern:
            continue
        # 合并同名话题：追加示例问法
        key = topic.casefold()
        examples = _str_list(item.get("示例问法"))
        if key in seen_topics:
            existing = next(x for x in out if x.话题.casefold() == key)
            for q in examples:
                if q not in existing.示例问法:
                    existing.示例问法.append(q)
            continue
        seen_topics.add(key)
        out.append(
            ConcernItem(
                话题=topic,
                顾虑=concern,
                触发情境=str(item.get("触发情境", "") or "").strip(),
                示例问法=examples,
                训练目标=str(item.get("训练目标", "") or "").strip(),
            )
        )

    if len(out) > topic_max:
        out = out[:topic_max]

    return ConcernPoolResult(
        items=out,
        raw_text=raw_text,
        raw=raw or {},
        usage=usage or {},
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ConcernPoolAgent:
    def __init__(
        self,
        config: ConcernPoolConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or ConcernPoolConfig.from_env()
        self._client = client
        self._owns_client = client is None
        self._skill: str | None = None

    def _make_client(self, *, trust_env: bool) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.config.timeout,
            trust_env=trust_env,
        )

    async def __aenter__(self) -> ConcernPoolAgent:
        if self._client is None:
            self.config.require_api_key()
            self._client = self._make_client(trust_env=self.config.trust_env)
        self._skill = load_skill(self.config.skill_path)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "ConcernPoolAgent 未初始化：请使用 `async with ConcernPoolAgent(...)`"
            )
        return self._client

    async def _rebuild_client_without_proxy(self) -> None:
        if not self._owns_client:
            return
        old = self._client
        self._client = self._make_client(trust_env=False)
        self.config.trust_env = False
        if old is not None:
            await old.aclose()
        logger.warning(
            "HTTP 代理连接失败，已改用直连（可用 --no-proxy 或 ARK_NO_PROXY=1）"
        )

    @property
    def skill(self) -> str:
        if self._skill is None:
            self._skill = load_skill(self.config.skill_path)
        return self._skill

    async def _chat(self, messages: list[dict[str, str]]) -> tuple[str, dict, dict]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        logger.debug(
            "Concern pool chat model=%s messages=%d",
            self.config.model,
            len(messages),
        )

        async def _post() -> httpx.Response:
            return await self._ensure_client().post("/chat/completions", json=body)

        try:
            resp = await _post()
        except httpx.ConnectError:
            if not self.config.trust_env or not self._owns_client:
                raise
            await self._rebuild_client_without_proxy()
            resp = await _post()

        if resp.status_code >= 400:
            raise RuntimeError(
                f"方舟 Chat Completions 失败 HTTP {resp.status_code}: {resp.text[:800]}"
            )
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"方舟响应格式异常: {data!r}") from exc
        usage = data.get("usage") or {}
        return text.strip(), data, usage if isinstance(usage, dict) else {}

    async def generate(
        self,
        *,
        background: Path | str | dict[str, Any],
        training_material: Path | str,
    ) -> ConcernPoolResult:
        bg = load_background(background)
        if isinstance(training_material, Path) or Path(str(training_material)).is_file():
            training = load_text(training_material)
        else:
            training = str(training_material)

        messages = [
            {
                "role": "system",
                "content": build_system_prompt(
                    self.skill,
                    topic_min=self.config.topic_min,
                    topic_max=self.config.topic_max,
                ),
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    background=bg,
                    training_material=training,
                ),
            },
        ]
        text, raw, usage = await self._chat(messages)
        parsed = parse_concern_pool_json(text)
        return normalize_concern_pool(
            parsed,
            topic_min=self.config.topic_min,
            topic_max=self.config.topic_max,
            raw_text=text,
            raw=raw,
            usage=usage,
        )


async def generate_concern_pool(
    *,
    background: Path | str | dict[str, Any],
    training_material: Path | str,
    config: ConcernPoolConfig | None = None,
) -> ConcernPoolResult:
    async with ConcernPoolAgent(config) as agent:
        return await agent.generate(
            background=background,
            training_material=training_material,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="入组前患者顾虑池生成")
    p.add_argument(
        "--background",
        "-b",
        default=str(_DEFAULT_BACKGROUND),
        help="研究背景 JSON 路径",
    )
    p.add_argument(
        "--training",
        "-t",
        default=str(_DEFAULT_TRAINING),
        help="培训材料 Markdown 路径",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="输出 JSON 路径（默认 questions_pool/<stem>.concerns.json）",
    )
    p.add_argument(
        "--out-dir",
        default=str(_DEFAULT_OUT_DIR),
        help="未指定 -o 时的输出目录",
    )
    p.add_argument("--no-proxy", action="store_true", help="忽略系统/环境 HTTP 代理")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


async def _amain(argv: Iterable[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = ConcernPoolConfig.from_env(
        trust_env=False if args.no_proxy else None,
    )
    try:
        config.require_api_key()
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    bg_path = Path(args.background)
    training_path = Path(args.training)
    if not bg_path.is_file():
        print(f"[FAIL] 研究背景不存在: {bg_path}", file=sys.stderr)
        return 1
    if not training_path.is_file():
        print(f"[FAIL] 培训材料不存在: {training_path}", file=sys.stderr)
        return 1

    out_path = (
        Path(args.output)
        if args.output
        else default_output_path(bg_path, Path(args.out_dir))
    )

    try:
        async with ConcernPoolAgent(config) as agent:
            result = await agent.generate(
                background=bg_path,
                training_material=training_path,
            )
    except httpx.ConnectError as exc:
        print(
            "[FAIL] 无法连接方舟 API（ConnectError）。\n"
            "可启动本地代理，或加 --no-proxy 直连。\n"
            f"详情: {exc}",
            file=sys.stderr,
        )
        return 1

    payload = result.to_list()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(
        f"wrote {out_path} topics={len(payload)} "
        f"(expect {config.topic_min}-{config.topic_max}) model={config.model}",
        file=sys.stderr,
    )
    if len(payload) < config.topic_min:
        print(
            f"[WARN] 话题数 {len(payload)} 少于下限 {config.topic_min}",
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain(sys.argv[1:])))


if __name__ == "__main__":
    main()
