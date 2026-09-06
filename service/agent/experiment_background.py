"""火山方舟 — CDE 登记资料 → 患者交流模拟用研究背景提炼 Agent。

技能说明：
  service/skills/experiment_background.md

API（OpenAI 兼容 Chat Completions，密钥用 TEXT_GENERATION_API_KEY）：
  POST {base_url}/chat/completions
  Authorization: Bearer <TEXT_GENERATION_API_KEY>

用途：
  将药物临床试验登记与信息公示平台（CDE）结构化 JSON，
  整理成 CRC 患者交流模拟可用的研究背景摘要。
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

# ===========================================================================
# 默认配置
# ===========================================================================
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-character-251128"
DEFAULT_TEMPERATURE = 0.1  # 提炼宜忠实，温度偏低
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 120.0

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_SKILL_PATH = _SERVICE_ROOT / "skills" / "experiment_background.md"
# 与 study_paths.DEFAULT_STUDY 保持一致（此处硬编码避免 import 期依赖）
_DEFAULT_STUDY = "Chronic rhinosinusitis with nasal polyps"
_DEFAULT_INPUT = (
    _SERVICE_ROOT
    / "acknowledge"
    / "relative_experiment"
    / f"{_DEFAULT_STUDY}.json"
)
_DEFAULT_OUTPUT = (
    _SERVICE_ROOT
    / "acknowledge"
    / "relative_experiment"
    / f"{_DEFAULT_STUDY}.background.json"
)

OUTPUT_KEYS = (
    "研究登记号",
    "药物",
    "疾病",
    "研究设计",
    "给药安排",
    "入选标准",
    "排除标准",
    "其他已知信息",
    "未提供的信息",
)

OUTPUT_SCHEMA_EXAMPLE = {
    "研究登记号": "CTR20263389",
    "药物": "CM512注射液",
    "疾病": "慢性鼻窦炎伴鼻息肉",
    "研究设计": "随机、双盲、安慰剂平行对照Ⅲ期研究",
    "给药安排": "登记资料写明皮下注射，每24周给药一次，多次",
    "入选标准": ["实际保存全部原文"],
    "排除标准": ["实际保存全部原文"],
    "其他已知信息": [
        "导入期涉及背景治疗和日记卡依从性要求",
        "登记资料显示有保险，具体条款未提供",
    ],
    "未提供的信息": [
        "完整到院安排",
        "单次访视耗时",
        "研究总时长",
        "具体费用和补贴安排",
    ],
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@dataclass
class BackgroundConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT
    skill_path: Path = _SKILL_PATH
    # 用源 JSON 覆盖模型返回的入排标准，保证「逐条原文」
    preserve_criteria_verbatim: bool = True
    # False 时忽略系统/环境 HTTP 代理（Clash 等未启动时常导致 ConnectError）
    trust_env: bool = True

    @classmethod
    def from_env(cls, **overrides: Any) -> BackgroundConfig:
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
                os.getenv("ARK_BG_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "max_tokens": int(
                os.getenv("ARK_BG_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
            ),
            "timeout": float(os.getenv("ARK_TIMEOUT", str(DEFAULT_TIMEOUT))),
            "trust_env": not no_proxy,
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
class ExperimentBackground:
    """一次提炼结果。"""

    研究登记号: str = ""
    药物: str = ""
    疾病: str = ""
    研究设计: str = ""
    给药安排: str = ""
    入选标准: list[str] = field(default_factory=list)
    排除标准: list[str] = field(default_factory=list)
    其他已知信息: list[str] = field(default_factory=list)
    未提供的信息: list[str] = field(default_factory=list)
    raw_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_meta: bool = False) -> dict[str, Any]:
        data = {k: getattr(self, k) for k in OUTPUT_KEYS}
        if include_meta:
            data["_meta"] = {
                "raw_text": self.raw_text,
                "usage": self.usage,
            }
        return data


# ---------------------------------------------------------------------------
# Skill / prompt
# ---------------------------------------------------------------------------
def load_skill(path: Path | None = None) -> str:
    p = path or _SKILL_PATH
    if not p.is_file():
        raise FileNotFoundError(f"技能说明文件不存在: {p}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"技能说明文件为空: {p}")
    return text


def load_cde_json(path: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path, dict):
        return path
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"CDE JSON 不存在: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"CDE JSON 根节点必须是对象: {p}")
    return data


def extract_criteria_from_source(cde: dict[str, Any]) -> tuple[list[str], list[str]]:
    """从源 JSON 直接取出入排标准原文列表。"""
    subjects = (cde.get("clinical_trial") or {}).get("subjects") or {}
    inclusion = subjects.get("inclusion_criteria") or []
    exclusion = subjects.get("exclusion_criteria") or []

    def _list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(x) for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    return _list(inclusion), _list(exclusion)


def build_system_prompt(skill: str) -> str:
    schema_text = json.dumps(OUTPUT_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return (
        "你是临床试验资料整理助手，服务于 CRC 患者交流模拟训练。\n"
        "请严格依据下方技能说明，把用户提供的 CDE 登记 JSON 整理成研究背景。\n\n"
        "【技能说明】\n"
        f"{skill.strip()}\n\n"
        "【任务提示词】\n"
        "将CDE数据整理成患者交流模拟使用的研究背景。\n\n"
        "要求：\n"
        "1. 提取药物、疾病、研究设计、给药安排及其他患者相关信息。\n"
        "2. 入排标准逐条保留原文。\n"
        "3. 未提供的信息明确列出，不自行补充。\n"
        "4. 给药间隔不等于到院间隔，评估时间不等于研究总时长。\n"
        "5. 不需要给每条信息添加ID和来源。\n\n"
        "【输出 Schema 示例】\n"
        f"{schema_text}\n\n"
        "只输出一个 JSON 对象，字段名与示例完全一致；不要 markdown 代码块，不要其它说明。"
    )


def build_user_prompt(cde: dict[str, Any]) -> str:
    # 去掉体积大且与患者沟通无关的冗余（保留完整结构即可；整份 JSON 通常可接受）
    payload = json.dumps(cde, ensure_ascii=False, indent=2)
    return (
        "请根据以下 CDE 登记资料 JSON，按系统要求输出研究背景 JSON。\n\n"
        f"{payload}"
    )


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def parse_background_json(text: str) -> dict[str, Any]:
    """从模型输出中提取研究背景 JSON。"""
    raw = text.strip()
    if not raw:
        raise ValueError("模型返回为空，无法解析研究背景")

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    match = _JSON_OBJECT_RE.search(raw)
    if match:
        candidates.insert(0, match.group(0))

    last_err: Exception | None = None
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
        if isinstance(data, dict):
            return data
    raise ValueError(f"无法解析研究背景 JSON: {last_err}; 原文前 200 字={raw[:200]!r}")


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_background(
    data: dict[str, Any],
    *,
    source: dict[str, Any] | None = None,
    preserve_criteria_verbatim: bool = True,
    raw_text: str = "",
    raw: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> ExperimentBackground:
    """规整模型输出；可选用以源 JSON 覆盖入排标准。"""
    inclusion = _str_list(data.get("入选标准"))
    exclusion = _str_list(data.get("排除标准"))

    if preserve_criteria_verbatim and source is not None:
        src_in, src_ex = extract_criteria_from_source(source)
        if src_in:
            inclusion = src_in
        if src_ex:
            exclusion = src_ex

    return ExperimentBackground(
        研究登记号=str(data.get("研究登记号", "") or "").strip(),
        药物=str(data.get("药物", "") or "").strip(),
        疾病=str(data.get("疾病", "") or "").strip(),
        研究设计=str(data.get("研究设计", "") or "").strip(),
        给药安排=str(data.get("给药安排", "") or "").strip(),
        入选标准=inclusion,
        排除标准=exclusion,
        其他已知信息=_str_list(data.get("其他已知信息")),
        未提供的信息=_str_list(data.get("未提供的信息")),
        raw_text=raw_text,
        raw=raw or {},
        usage=usage or {},
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ExperimentBackgroundAgent:
    """调用方舟大模型，按 experiment_background.md 提炼研究背景。"""

    def __init__(
        self,
        config: BackgroundConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or BackgroundConfig.from_env()
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

    async def __aenter__(self) -> ExperimentBackgroundAgent:
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
                "ExperimentBackgroundAgent 未初始化：请使用 "
                "`async with ExperimentBackgroundAgent(...)`"
            )
        return self._client

    async def _rebuild_client_without_proxy(self) -> None:
        """系统代理不可用时，关闭旧客户端并以 trust_env=False 重建。"""
        if not self._owns_client:
            return
        old = self._client
        self._client = self._make_client(trust_env=False)
        self.config.trust_env = False
        if old is not None:
            await old.aclose()
        logger.warning(
            "HTTP 代理连接失败，已改用直连（可用 --no-proxy 或 ARK_NO_PROXY=1 固定此行为）"
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
            "Background chat model=%s messages=%d", self.config.model, len(messages)
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

    async def extract(
        self,
        cde: Path | str | dict[str, Any],
    ) -> ExperimentBackground:
        """从 CDE JSON（路径或 dict）提炼研究背景。"""
        source = load_cde_json(cde)
        messages = [
            {"role": "system", "content": build_system_prompt(self.skill)},
            {"role": "user", "content": build_user_prompt(source)},
        ]
        text, raw, usage = await self._chat(messages)
        parsed = parse_background_json(text)
        return normalize_background(
            parsed,
            source=source,
            preserve_criteria_verbatim=self.config.preserve_criteria_verbatim,
            raw_text=text,
            raw=raw,
            usage=usage,
        )


async def extract_experiment_background(
    cde: Path | str | dict[str, Any],
    *,
    config: BackgroundConfig | None = None,
) -> ExperimentBackground:
    async with ExperimentBackgroundAgent(config) as agent:
        return await agent.extract(cde)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    from service.agent.study_paths import DEFAULT_STUDY

    p = argparse.ArgumentParser(
        description="CDE 登记资料 → 患者交流模拟研究背景提炼"
    )
    p.add_argument(
        "--study",
        default=DEFAULT_STUDY,
        help=f"研究 stem（默认 {DEFAULT_STUDY}）；决定默认 -i/-o",
    )
    p.add_argument(
        "--input",
        "-i",
        default=None,
        help="CDE JSON 路径（默认 acknowledge/relative_experiment/<study>.json）",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="输出 JSON；默认写入 <study>.background.json（加 --stdout 仅打印）",
    )
    p.add_argument(
        "--stdout",
        action="store_true",
        help="只打印到 stdout，不写文件",
    )
    p.add_argument(
        "--no-preserve-criteria",
        action="store_true",
        help="不强制用源 JSON 覆盖入排标准（默认覆盖以保证原文）",
    )
    p.add_argument(
        "--no-proxy",
        action="store_true",
        help="忽略系统/环境 HTTP 代理直连方舟（Clash 未开时用）",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p


async def _amain(argv: Iterable[str] | None = None) -> int:
    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from service.agent.study_paths import resolve_study

    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    paths = resolve_study(args.study)
    input_path = Path(args.input) if args.input else paths.cde_json
    output_path: Path | None
    if args.stdout:
        output_path = None
    elif args.output:
        output_path = Path(args.output)
    else:
        output_path = paths.background

    config = BackgroundConfig.from_env(
        preserve_criteria_verbatim=not args.no_preserve_criteria,
        trust_env=False if args.no_proxy else None,
    )
    try:
        config.require_api_key()
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if not input_path.is_file():
        print(f"[FAIL] CDE JSON 不存在: {input_path}", file=sys.stderr)
        return 1

    try:
        async with ExperimentBackgroundAgent(config) as agent:
            result = await agent.extract(input_path)
    except httpx.ConnectError as exc:
        print(
            "[FAIL] 无法连接方舟 API（ConnectError）。\n"
            "本机系统代理当前为 127.0.0.1:10809（常见于 Clash）。\n"
            "请任选其一：\n"
            "  1) 启动本地代理；\n"
            "  2) 重试并加 --no-proxy；\n"
            "  3) 在 Windows「代理设置」中关闭系统代理。\n"
            f"详情: {exc}",
            file=sys.stderr,
        )
        return 1

    payload = result.to_dict()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {output_path}", file=sys.stderr)
    else:
        print(text)

    print(
        f"model={config.model} "
        f"inclusion={len(result.入选标准)} exclusion={len(result.排除标准)}",
        file=sys.stderr,
    )
    return 0 if result.研究登记号 or result.药物 else 2


def main() -> None:
    raise SystemExit(asyncio.run(_amain(sys.argv[1:])))


if __name__ == "__main__":
    main()
