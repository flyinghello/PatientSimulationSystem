"""火山方舟 — doubao-seed-character 情景扮演问题生成 Agent。

模型详情：
https://console.volcengine.com/ark/region:cn-beijing/model/detail?name=doubao-seed-character

API（OpenAI 兼容 Chat Completions）：
  POST {base_url}/chat/completions
  Authorization: Bearer <ARK_API_KEY>
  model: doubao-seed-character-251128 或控制台推理接入点 ep-xxx

用途：
  在 CRC 沟通训练中扮演临床试验受试者/患者，按人设与情景生成追问、疑虑类问题；
  支持一次性批量出题，也支持多轮对话中按 CRC 回复生成下一句患者提问。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ===========================================================================
# 默认配置（密钥写在项目根目录 .env）
# ===========================================================================
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
# 也可改为控制台「在线推理」接入点 ID，例如 ep-2025xxxxxxxxxx
DEFAULT_MODEL = "doubao-seed-character-251128"
DEFAULT_TEMPERATURE = 0.85
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT = 60.0

_COMMON_QUESTIONS_PATH = (
    Path(__file__).resolve().parents[1] / "acknowledge" / "common_questions.txt"
)

# 默认人设：临床试验知情沟通场景下的受试者
DEFAULT_PERSONA = (
    "你是一名即将（或正在）参加新药临床试验的受试者。"
    "你关心费用、安慰剂、副作用、随访时间、知情同意与隐私。"
    "说话口语化、带一点焦虑或犹豫，但不要攻击工作人员。"
    "不要扮演医生或 CRC，不要讲解专业知识，只以患者身份提问或表达顾虑。"
)

DEFAULT_SYSTEM_RULES = (
    "【输出要求】\n"
    "1. 始终保持上述患者人设，使用第一人称。\n"
    "2. 问题要具体、口语化，一次只问一件事（除非用户明确要求多条）。\n"
    "3. 不要编造未给出的检查结果或医生诊断；不确定时用疑问句表达担心。\n"
    "4. 不要承诺疗效，也不要替 CRC 做决定。\n"
    "5. 若要求输出多条问题，请按 JSON 数组返回纯字符串列表，不要加 markdown 代码块。"
)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@dataclass
class ChatMessage:
    role: str  # system / user / assistant
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class ScenarioSpec:
    """一次情景扮演的场景描述。"""

    title: str = "新药临床试验知情同意沟通"
    disease: str = "高血压"
    trial_phase: str = "II 期"
    site: str = "三甲医院临床试验中心"
    patient_profile: str = "55 岁，初中文化，首次参加临床试验，对安慰剂和费用比较敏感"
    crc_goal: str = "完成知情沟通，解答受试者疑虑"
    focus_topics: list[str] = field(
        default_factory=lambda: [
            "费用与补偿",
            "安慰剂与盲态",
            "安全性与副作用",
            "随访时间与流程",
            "知情同意与隐私",
        ]
    )
    extra: str = ""

    def render(self) -> str:
        topics = "、".join(self.focus_topics) if self.focus_topics else "通用疑虑"
        parts = [
            f"情景标题：{self.title}",
            f"适应症/疾病：{self.disease}",
            f"试验阶段：{self.trial_phase}",
            f"沟通地点：{self.site}",
            f"患者画像：{self.patient_profile}",
            f"CRC 训练目标：{self.crc_goal}",
            f"关注话题：{topics}",
        ]
        if self.extra.strip():
            parts.append(f"补充设定：{self.extra.strip()}")
        return "\n".join(parts)


@dataclass
class QuestionConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT
    persona: str = DEFAULT_PERSONA
    system_rules: str = DEFAULT_SYSTEM_RULES

    @classmethod
    def from_env(cls, **overrides: Any) -> QuestionConfig:
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
                    val = getattr(cfg, key, None)
                    if val and str(val).strip():
                        return str(val).strip()
            return default

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
                os.getenv("ARK_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "max_tokens": int(os.getenv("ARK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            "timeout": float(os.getenv("ARK_TIMEOUT", str(DEFAULT_TIMEOUT))),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def require_api_key(self) -> None:
        if not self.api_key:
            raise ValueError(
                "缺少鉴权信息：请在项目根目录 .env 中设置 TEXT_GENERATION_API_KEY "
                "（或 ARK_API_KEY）"
            )


@dataclass
class GenerateResult:
    """一次生成的结果。"""

    text: str
    questions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------
def load_common_questions(path: Path | None = None) -> str:
    """读取常见问题库，作为 few-shot / 风格参考（可选）。"""
    p = path or _COMMON_QUESTIONS_PATH
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("无法读取常见问题库 %s: %s", p, exc)
        return ""


def build_system_prompt(
    *,
    persona: str = DEFAULT_PERSONA,
    system_rules: str = DEFAULT_SYSTEM_RULES,
    scenario: ScenarioSpec | None = None,
    reference_questions: str | None = None,
) -> str:
    blocks = [
        "你正在参与 CRC（临床试验协调员）沟通能力训练中的情景扮演。",
        persona.strip(),
        system_rules.strip(),
    ]
    if scenario is not None:
        blocks.append("【当前情景】\n" + scenario.render())
    if reference_questions and reference_questions.strip():
        # 截断过长参考，避免占用过多上下文
        ref = reference_questions.strip()
        if len(ref) > 3500:
            ref = ref[:3500] + "\n…（已截断）"
        blocks.append(
            "【常见问题风格参考，请模仿口语与话题分布，不要原样照抄】\n" + ref
        )
    return "\n\n".join(blocks)


def build_batch_user_prompt(
    count: int,
    *,
    topic: str | None = None,
    crc_utterance: str | None = None,
) -> str:
    topic_line = f"优先围绕「{topic}」提问。" if topic else "话题可覆盖费用、安慰剂、副作用、随访、知情等。"
    crc_line = (
        f"CRC 刚刚说：{crc_utterance.strip()}\n请据此提出患者可能接着问的问题。"
        if crc_utterance and crc_utterance.strip()
        else "请根据情景生成患者主动会问的问题。"
    )
    return (
        f"请生成 {count} 条彼此不重复的患者提问。\n"
        f"{topic_line}\n"
        f"{crc_line}\n"
        "只输出 JSON 字符串数组，例如：[\"问题1\",\"问题2\"]，不要其它说明。"
    )


def build_turn_user_prompt(crc_utterance: str) -> str:
    return (
        "CRC 对你说：\n"
        f"「{crc_utterance.strip()}」\n\n"
        "请以患者身份回应：可以先简短表态，再提出 1 个最想追问的问题。"
        "不要一次问很多个，也不要跳出人设。"
    )


_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def parse_question_list(text: str) -> list[str]:
    """从模型输出中解析问题列表；失败时按行拆分兜底。"""
    raw = text.strip()
    if not raw:
        return []

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    match = _JSON_ARRAY_RE.search(raw)
    if match:
        candidates.insert(0, match.group(0))

    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out = [str(x).strip() for x in data if str(x).strip()]
            if out:
                return out
        if isinstance(data, dict):
            for key in ("questions", "items", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    out = [str(x).strip() for x in val if str(x).strip()]
                    if out:
                        return out

    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^(\d+[\.\)、]|\-|\*|•)\s*", "", s)
        s = s.strip("「」\"'“”")
        if s:
            lines.append(s)
    return lines


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class QuestionsGenerateAgent:
    """调用 doubao-seed-character，生成情景扮演中的患者问题。"""

    def __init__(
        self,
        config: QuestionConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or QuestionConfig.from_env()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> QuestionsGenerateAgent:
        if self._client is None:
            self.config.require_api_key()
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "QuestionsGenerateAgent 未初始化：请使用 `async with QuestionsGenerateAgent(...)`"
            )
        return self._client

    def _messages_payload(
        self,
        messages: Sequence[ChatMessage | dict[str, str]],
    ) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for m in messages:
            if isinstance(m, ChatMessage):
                out.append(m.to_dict())
            else:
                out.append({"role": str(m["role"]), "content": str(m["content"])})
        return out

    async def chat(
        self,
        messages: Sequence[ChatMessage | dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> GenerateResult:
        """底层 Chat Completions 调用（非流式）。"""
        if stream:
            raise ValueError("chat() 不支持 stream=True，请使用 stream_chat()")

        client = self._ensure_client()
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": self._messages_payload(messages),
            "temperature": (
                self.config.temperature if temperature is None else temperature
            ),
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        logger.debug("Ark chat request model=%s messages=%d", self.config.model, len(body["messages"]))
        resp = await client.post("/chat/completions", json=body)
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
        return GenerateResult(
            text=text.strip(),
            questions=parse_question_list(text),
            raw=data,
            usage=usage if isinstance(usage, dict) else {},
        )

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage | dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """流式输出 assistant 文本增量。"""
        client = self._ensure_client()
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": self._messages_payload(messages),
            "temperature": (
                self.config.temperature if temperature is None else temperature
            ),
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": True,
        }
        async with client.stream("POST", "/chat/completions", json=body) as resp:
            if resp.status_code >= 400:
                err = await resp.aread()
                raise RuntimeError(
                    f"方舟流式调用失败 HTTP {resp.status_code}: {err[:800]!r}"
                )
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content")
                if piece:
                    yield piece

    async def generate_questions(
        self,
        *,
        count: int = 5,
        scenario: ScenarioSpec | None = None,
        topic: str | None = None,
        crc_utterance: str | None = None,
        use_reference: bool = True,
        temperature: float | None = None,
    ) -> GenerateResult:
        """按情景批量生成患者问题。"""
        if count < 1:
            raise ValueError("count 必须 >= 1")

        ref = load_common_questions() if use_reference else ""
        system = build_system_prompt(
            persona=self.config.persona,
            system_rules=self.config.system_rules,
            scenario=scenario or ScenarioSpec(),
            reference_questions=ref or None,
        )
        user = build_batch_user_prompt(
            count, topic=topic, crc_utterance=crc_utterance
        )
        result = await self.chat(
            [
                ChatMessage("system", system),
                ChatMessage("user", user),
            ],
            temperature=temperature,
        )
        # 若模型未按 JSON 返回，questions 仍可能从行拆分得到；截断到 count
        if result.questions:
            result.questions = result.questions[:count]
        elif result.text:
            result.questions = [result.text]
        return result

    async def next_patient_question(
        self,
        crc_utterance: str,
        *,
        scenario: ScenarioSpec | None = None,
        history: Sequence[ChatMessage | dict[str, str]] | None = None,
        use_reference: bool = False,
        temperature: float | None = None,
    ) -> GenerateResult:
        """多轮情景：根据 CRC 刚说的话，生成患者下一句提问。"""
        if not crc_utterance.strip():
            raise ValueError("crc_utterance 不能为空")

        ref = load_common_questions() if use_reference else ""
        system = build_system_prompt(
            persona=self.config.persona,
            system_rules=self.config.system_rules,
            scenario=scenario or ScenarioSpec(),
            reference_questions=ref or None,
        )
        messages: list[ChatMessage | dict[str, str]] = [
            ChatMessage("system", system)
        ]
        if history:
            messages.extend(list(history))
        messages.append(ChatMessage("user", build_turn_user_prompt(crc_utterance)))
        return await self.chat(messages, temperature=temperature)


# ---------------------------------------------------------------------------
# Sync helpers（便于脚本快速调用）
# ---------------------------------------------------------------------------
async def generate_questions(
    count: int = 5,
    *,
    scenario: ScenarioSpec | None = None,
    topic: str | None = None,
    crc_utterance: str | None = None,
    config: QuestionConfig | None = None,
) -> GenerateResult:
    async with QuestionsGenerateAgent(config) as agent:
        return await agent.generate_questions(
            count=count,
            scenario=scenario,
            topic=topic,
            crc_utterance=crc_utterance,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="情景扮演患者问题生成（doubao-seed-character）")
    p.add_argument("--count", type=int, default=5, help="批量生成问题条数")
    p.add_argument("--topic", default=None, help="聚焦话题，如 费用与补偿")
    p.add_argument(
        "--crc",
        default=None,
        help="CRC 刚说的话；提供时按对话生成追问",
    )
    p.add_argument("--disease", default="高血压")
    p.add_argument("--stream", action="store_true", help="流式输出下一句患者话（需 --crc）")
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

    config = QuestionConfig.from_env()
    scenario = ScenarioSpec(disease=args.disease)

    try:
        config.require_api_key()
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    async with QuestionsGenerateAgent(config) as agent:
        if args.crc and args.stream:
            print("=== 流式患者追问 ===")
            system = build_system_prompt(scenario=scenario)
            messages = [
                ChatMessage("system", system),
                ChatMessage("user", build_turn_user_prompt(args.crc)),
            ]
            buf: list[str] = []
            async for piece in agent.stream_chat(messages):
                print(piece, end="", flush=True)
                buf.append(piece)
            print()
            return 0 if "".join(buf).strip() else 2

        if args.crc and not args.stream:
            result = await agent.next_patient_question(
                args.crc, scenario=scenario
            )
            print(result.text)
            return 0 if result.text else 2

        result = await agent.generate_questions(
            count=args.count,
            scenario=scenario,
            topic=args.topic,
            crc_utterance=args.crc,
        )
        print(f"model={config.model}")
        if result.usage:
            print(f"usage={result.usage}")
        print("---")
        if result.questions:
            for i, q in enumerate(result.questions, 1):
                print(f"{i}. {q}")
        else:
            print(result.text)
        return 0 if (result.questions or result.text) else 2


def main() -> None:
    import asyncio
    import sys

    raise SystemExit(asyncio.run(_amain(sys.argv[1:])))


if __name__ == "__main__":
    main()
