"""火山方舟 — CRC 沟通表现评分 Agent。

评分标准：
  service/skills/evaluate.md

API（OpenAI 兼容 Chat Completions，密钥用 TEXT_GENERATION_API_KEY）：
  POST {base_url}/chat/completions
  Authorization: Bearer <TEXT_GENERATION_API_KEY>

用途：
  根据 CRC 与患者的对话记录，按《CRC与患者交流评判标准》打分，
  输出各维度分数、合格判定、改进建议与总分。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ===========================================================================
# 默认配置（密钥写在项目根目录 .env：TEXT_GENERATION_API_KEY）
# ===========================================================================
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed-character-251128"
DEFAULT_TEMPERATURE = 0.2  # 评分宜稳定，温度偏低
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TIMEOUT = 90.0

_RUBRIC_PATH = Path(__file__).resolve().parents[1] / "skills" / "evaluate.md"

# 与 evaluate.md 对齐的评分维度（入组前；不含随访）
RUBRIC_DIMENSIONS: dict[str, list[str]] = {
    "沟通准备": ["信息传递", "知情同意", "个性化适配"],
    "沟通态度": ["耐心程度", "共情能力", "尊重程度"],
    "合规性": ["知情沟通合规"],
}
EXPECTED_DIMENSION_COUNT = sum(len(v) for v in RUBRIC_DIMENSIONS.values())

CORE_PRINCIPLES = ["以患者为中心", "双向尊重", "持续耐心"]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@dataclass
class ChatMessage:
    role: str  # system / user / assistant / patient / crc
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class DimensionScore:
    category: str
    dimension: str
    score: float  # 0~100
    passed: bool
    evidence: str = ""
    suggestion: str = ""


@dataclass
class EvaluationReport:
    """一次评分结果。"""

    overall_score: float
    passed: bool
    summary: str
    dimensions: list[DimensionScore] = field(default_factory=list)
    principles: dict[str, str] = field(default_factory=dict)
    strengths: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    raw_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("raw", None)  # 体积大，默认不随业务 dict 暴露
        return data


@dataclass
class EvalConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT
    rubric_path: Path = _RUBRIC_PATH
    pass_score: float = 70.0  # 维度/总分合格线
    trust_env: bool = True

    @classmethod
    def from_env(cls, **overrides: Any) -> EvalConfig:
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
                    # setting 里 TEXT_GENERATION_* 已映射为 ARK_*
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

        rubric = overrides.pop("rubric_path", None)
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
                os.getenv("ARK_EVAL_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "max_tokens": int(
                os.getenv("ARK_EVAL_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
            ),
            "timeout": float(os.getenv("ARK_TIMEOUT", str(DEFAULT_TIMEOUT))),
            "pass_score": float(os.getenv("ARK_EVAL_PASS_SCORE", "70")),
            "trust_env": True,
        }
        if rubric is not None:
            values["rubric_path"] = Path(rubric)
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def require_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "缺少鉴权信息：请在项目根目录 .env 中设置 TEXT_GENERATION_API_KEY"
            )


# ---------------------------------------------------------------------------
# Rubric / prompt
# ---------------------------------------------------------------------------
def load_rubric(path: Path | None = None) -> str:
    """读取评分标准 Markdown。"""
    p = path or _RUBRIC_PATH
    if not p.is_file():
        raise FileNotFoundError(f"评分标准文件不存在: {p}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"评分标准文件为空: {p}")
    return text


def format_dialogue(
    dialogue: Sequence[ChatMessage | dict[str, str]] | str,
) -> str:
    """把对话整理成可读文本。支持字符串或消息列表。

    角色约定与 patient_turn 一致：
      patient / assistant → 患者
      crc / user → CRC（受训者）
    """
    if isinstance(dialogue, str):
        return dialogue.strip()

    lines: list[str] = []
    for i, item in enumerate(dialogue, 1):
        if isinstance(item, ChatMessage):
            role, content = item.role, item.content
        else:
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))
        role_zh = {
            "patient": "患者",
            "crc": "CRC",
            "user": "CRC",
            "assistant": "患者",
            "system": "系统",
        }.get(role.lower(), role)
        lines.append(f"{i}. 【{role_zh}】{content.strip()}")
    return "\n".join(lines)


def load_session_dialogue(session_dir: Path) -> list[dict[str, str]]:
    """从 patient_turn 会话目录读取 dialogue.jsonl。"""
    dpath = session_dir / "dialogue.jsonl"
    if not dpath.is_file():
        raise FileNotFoundError(f"会话对话文件不存在: {dpath}")
    dialogue: list[dict[str, str]] = []
    for line in dpath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        if isinstance(item, dict):
            dialogue.append(
                {
                    "role": str(item.get("role", "")),
                    "content": str(item.get("content", "")),
                }
            )
    if not dialogue:
        raise ValueError(f"会话对话为空: {dpath}")
    return dialogue


def build_system_prompt(rubric: str) -> str:
    dim_lines: list[str] = []
    for cat, dims in RUBRIC_DIMENSIONS.items():
        dim_lines.append(f"- {cat}：{ '、'.join(dims) }")
    dims_block = "\n".join(dim_lines)
    principles = "、".join(CORE_PRINCIPLES)

    return (
        "你是临床试验沟通培训的资深考评官，负责评估 CRC（临床试验协调员）"
        "与患者/受试者的交流表现。\n"
        "请严格依据下方《CRC与患者交流评判标准》打分，不要引入标准外的苛刻要求。\n\n"
        "【评分标准】\n"
        f"{rubric.strip()}\n\n"
        "【评分维度】\n"
        f"{dims_block}\n"
        f"- 核心原则（文字评价，不单独打分）：{principles}\n\n"
        "【评分规则】\n"
        "1. 每个维度打 0~100 分；>=70 视为该维度合格（passed=true）。\n"
        "2. overall_score 为各维度算术平均，保留 1 位小数。\n"
        "3. 本标准仅用于入组前知情沟通；不要评分「随访关怀」或任何随访相关维度。\n"
        "4. 对话中未充分体现的维度：根据 CRC 是否本应主动覆盖判断；"
        "可酌情给分，并在 evidence 说明依据。\n"
        "5. evidence 须引用对话中的具体表述；suggestion 给出可执行改进点。\n"
        "6. 只输出一个 JSON 对象，不要 markdown 代码块，不要其它说明。\n\n"
        "【JSON Schema】\n"
        "{\n"
        '  "overall_score": 85.0,\n'
        '  "passed": true,\n'
        '  "summary": "一句话总评",\n'
        '  "dimensions": [\n'
        "    {\n"
        '      "category": "沟通准备",\n'
        '      "dimension": "信息传递",\n'
        '      "score": 80,\n'
        '      "passed": true,\n'
        '      "evidence": "...",\n'
        '      "suggestion": "..."\n'
        "    }\n"
        "  ],\n"
        '  "principles": {\n'
        '    "以患者为中心": "...",\n'
        '    "双向尊重": "...",\n'
        '    "持续耐心": "..."\n'
        "  },\n"
        '  "strengths": ["..."],\n'
        '  "improvements": ["..."]\n'
        "}\n"
        f"dimensions 必须覆盖全部 {EXPECTED_DIMENSION_COUNT} 个维度"
        "（沟通准备 3 + 沟通态度 3 + 合规性 1），不得遗漏，不得增加随访类维度。"
    )


def build_user_prompt(
    dialogue_text: str,
    *,
    scenario: str | None = None,
    trainee_name: str | None = None,
) -> str:
    parts = ["请评估以下 CRC 与患者的沟通表现，并按要求输出 JSON。"]
    if trainee_name:
        parts.append(f"受训 CRC：{trainee_name}")
    if scenario and scenario.strip():
        parts.append(f"【情景说明】\n{scenario.strip()}")
    parts.append(f"【对话记录】\n{dialogue_text.strip()}")
    return "\n\n".join(parts)


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def parse_evaluation_json(text: str) -> dict[str, Any]:
    """从模型输出中提取评分 JSON。"""
    raw = text.strip()
    if not raw:
        raise ValueError("模型返回为空，无法解析评分结果")

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
    raise ValueError(f"无法解析评分 JSON: {last_err}; 原文前 200 字={raw[:200]!r}")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_report(
    data: dict[str, Any],
    *,
    raw_text: str = "",
    raw: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
    pass_score: float = 70.0,
) -> EvaluationReport:
    """把模型 JSON 规整为 EvaluationReport，补齐缺失维度。"""
    dims_in = data.get("dimensions") or []
    by_key: dict[tuple[str, str], DimensionScore] = {}

    if isinstance(dims_in, list):
        for item in dims_in:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "")).strip()
            dimension = str(item.get("dimension", "")).strip()
            if not dimension:
                continue
            score = max(0.0, min(100.0, _as_float(item.get("score"), 0.0)))
            passed = bool(item.get("passed", score >= pass_score))
            by_key[(category, dimension)] = DimensionScore(
                category=category or "未分类",
                dimension=dimension,
                score=score,
                passed=passed,
                evidence=str(item.get("evidence", "") or "").strip(),
                suggestion=str(item.get("suggestion", "") or "").strip(),
            )

    dimensions: list[DimensionScore] = []
    for cat, dims in RUBRIC_DIMENSIONS.items():
        for dim in dims:
            existing = by_key.get((cat, dim))
            if existing is None:
                # 尝试仅按维度名匹配
                existing = next(
                    (v for (c, d), v in by_key.items() if d == dim),
                    None,
                )
            if existing is None:
                dimensions.append(
                    DimensionScore(
                        category=cat,
                        dimension=dim,
                        score=0.0,
                        passed=False,
                        evidence="模型未返回该维度",
                        suggestion="请重新评分或人工复核",
                    )
                )
            else:
                existing.category = cat
                existing.dimension = dim
                existing.passed = existing.score >= pass_score
                dimensions.append(existing)

    scores = [d.score for d in dimensions]
    overall = _as_float(data.get("overall_score"), 0.0)
    if scores:
        computed = round(sum(scores) / len(scores), 1)
        # 若模型总分缺失或明显离谱，用算术平均纠偏
        if "overall_score" not in data or abs(overall - computed) > 25:
            overall = computed
        else:
            overall = round(overall, 1)

    principles_raw = data.get("principles") or {}
    principles: dict[str, str] = {}
    if isinstance(principles_raw, dict):
        for name in CORE_PRINCIPLES:
            principles[name] = str(principles_raw.get(name, "") or "").strip()
        for k, v in principles_raw.items():
            if k not in principles:
                principles[str(k)] = str(v).strip()

    def _str_list(key: str) -> list[str]:
        val = data.get(key) or []
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    passed = bool(data.get("passed", overall >= pass_score))
    summary = str(data.get("summary", "") or "").strip()

    return EvaluationReport(
        overall_score=overall,
        passed=passed,
        summary=summary,
        dimensions=dimensions,
        principles=principles,
        strengths=_str_list("strengths"),
        improvements=_str_list("improvements"),
        raw_text=raw_text,
        raw=raw or {},
        usage=usage or {},
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class EvaluationAgent:
    """调用方舟大模型，按 evaluate.md 标准评估 CRC 沟通表现。"""

    def __init__(
        self,
        config: EvalConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or EvalConfig.from_env()
        self._client = client
        self._owns_client = client is None
        self._rubric: str | None = None

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

    async def __aenter__(self) -> EvaluationAgent:
        if self._client is None:
            self.config.require_api_key()
            self._client = self._make_client(trust_env=self.config.trust_env)
        self._rubric = load_rubric(self.config.rubric_path)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "EvaluationAgent 未初始化：请使用 `async with EvaluationAgent(...)`"
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
        logger.warning("HTTP 代理失败，已改用直连（可用 --no-proxy）")

    @property
    def rubric(self) -> str:
        if self._rubric is None:
            self._rubric = load_rubric(self.config.rubric_path)
        return self._rubric

    async def _chat(self, messages: list[dict[str, str]]) -> tuple[str, dict, dict]:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        logger.debug(
            "Eval chat model=%s messages=%d", self.config.model, len(messages)
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

    async def evaluate(
        self,
        dialogue: Sequence[ChatMessage | dict[str, str]] | str,
        *,
        scenario: str | None = None,
        trainee_name: str | None = None,
    ) -> EvaluationReport:
        """评估一段 CRC-患者对话。"""
        dialogue_text = format_dialogue(dialogue)
        if not dialogue_text:
            raise ValueError("对话内容为空，无法评分")

        messages = [
            {"role": "system", "content": build_system_prompt(self.rubric)},
            {
                "role": "user",
                "content": build_user_prompt(
                    dialogue_text,
                    scenario=scenario,
                    trainee_name=trainee_name,
                ),
            },
        ]
        text, raw, usage = await self._chat(messages)
        parsed = parse_evaluation_json(text)
        return normalize_report(
            parsed,
            raw_text=text,
            raw=raw,
            usage=usage,
            pass_score=self.config.pass_score,
        )


async def evaluate_dialogue(
    dialogue: Sequence[ChatMessage | dict[str, str]] | str,
    *,
    scenario: str | None = None,
    trainee_name: str | None = None,
    config: EvalConfig | None = None,
) -> EvaluationReport:
    async with EvaluationAgent(config) as agent:
        return await agent.evaluate(
            dialogue,
            scenario=scenario,
            trainee_name=trainee_name,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
_SAMPLE_DIALOGUE = [
    ChatMessage("patient", "参加这个试验药都是免费的吗？路费能报销吗？"),
    ChatMessage(
        "crc",
        "阿姨您放心，研究相关的检查和试验用药都是免费的。"
        "交通补贴按项目规定发放，具体金额我可以给您看知情同意书里的说明，"
        "您慢慢看，有不懂的地方随时问我。",
    ),
    ChatMessage("patient", "会不会分到安慰剂，吃不到新药啊？"),
    ChatMessage(
        "crc",
        "这项研究是随机双盲的，谁分到哪一组我们工作人员也不知道，"
        "这是为了结果更客观。不管分到哪一组，您的安全和随访都会有保障；"
        "如果不想参加，随时可以退出，不会影响您以后看病。",
    ),
]


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CRC 沟通表现评分（evaluate.md）")
    p.add_argument(
        "--dialogue",
        default=None,
        help="对话文本文件路径；不填且无 --session 时使用内置示例对话",
    )
    p.add_argument(
        "--session",
        "-s",
        default=None,
        help="patient_turn 会话目录（读取 dialogue.jsonl）",
    )
    p.add_argument("--trainee", default=None, help="受训 CRC 姓名")
    p.add_argument(
        "--scenario",
        default="临床试验入组前知情沟通",
        help="情景描述（入组前训练勿用随访场景名）",
    )
    p.add_argument("--no-proxy", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


async def _amain(argv: Iterable[str] | None = None) -> int:
    import sys

    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = EvalConfig.from_env(trust_env=False if args.no_proxy else None)
    try:
        config.require_api_key()
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.session:
        try:
            dialogue: Sequence[ChatMessage] | Sequence[dict[str, str]] | str = (
                load_session_dialogue(Path(args.session))
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[FAIL] 无法读取会话: {exc}", file=sys.stderr)
            return 1
    elif args.dialogue:
        dialogue = Path(args.dialogue).read_text(encoding="utf-8")
    else:
        dialogue = _SAMPLE_DIALOGUE

    try:
        async with EvaluationAgent(config) as agent:
            report = await agent.evaluate(
                dialogue,
                scenario=args.scenario,
                trainee_name=args.trainee,
            )
    except httpx.ConnectError as exc:
        print(f"[FAIL] 连接失败，可加 --no-proxy。详情: {exc}", file=sys.stderr)
        return 1

    print(f"model={config.model}")
    print(f"overall={report.overall_score} passed={report.passed}")
    print(f"summary={report.summary}")
    print("--- dimensions ---")
    for d in report.dimensions:
        flag = "PASS" if d.passed else "FAIL"
        print(f"[{flag}] {d.category}/{d.dimension}: {d.score:.0f}")
        if d.suggestion:
            print(f"       建议: {d.suggestion}")
    if report.improvements:
        print("--- improvements ---")
        for tip in report.improvements:
            print(f"- {tip}")
    return 0 if report.dimensions else 2


def main() -> None:
    import asyncio
    import sys

    raise SystemExit(asyncio.run(_amain(sys.argv[1:])))


if __name__ == "__main__":
    main()
