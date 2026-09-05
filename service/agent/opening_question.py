"""火山方舟 — 入组前首次提问 / 开局状态生成 Agent。

技能说明：
  service/skills/opening_question.md

输入：
  - 研究背景 JSON（experiment_background 产出）
  - 顾虑池 JSON（concern_pool 产出）
  - 患者特征：每次 generate 前先调用 service.agent.personality.sample_persona()
    （可用 -p 显式覆盖；--seed 传入采样种子）

输出 Schema：患者画像 + 状态 + 患者台词 + 是否结束
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
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 3072
DEFAULT_TIMEOUT = 120.0

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_SKILL_PATH = _SERVICE_ROOT / "skills" / "opening_question.md"
_DEFAULT_STUDY = "Chronic rhinosinusitis with nasal polyps"
_DEFAULT_BACKGROUND = (
    _SERVICE_ROOT
    / "acknowledge"
    / "relative_experiment"
    / f"{_DEFAULT_STUDY}.background.json"
)
_DEFAULT_CONCERNS = (
    _SERVICE_ROOT
    / "acknowledge"
    / "questions_pool"
    / f"{_DEFAULT_STUDY}.concerns.json"
)
_DEFAULT_OUT_DIR = _SERVICE_ROOT / "acknowledge" / "opening_state"

OUTPUT_SCHEMA_EXAMPLE = {
    "患者画像": {
        "年龄": 42,
        "学历": "本科",
        "健康信息理解能力": "低",
        "试验经历": "没有参加过",
        "交流特点": "谨慎，主动提问",
        "决策偏好": "想与家属商量",
        "陪同者": "无",
        "生活限制": ["工作日请假困难"],
        "疾病背景": "自述有鼻息肉，鼻塞伴嗅觉减退，具体病史待询问",
        "筛选状态": "尚未正式筛选",
    },
    "状态": {
        "主要顾虑": ["到院安排", "安慰剂分组"],
        "当前话题": "到院安排",
        "已理解": [],
        "尚不清楚": ["需要多久来一次医院"],
        "待核实事项": [],
        "已讨论清楚的话题": [],
        "当前情绪": "有些犹豫",
        "参与态度": "愿意了解",
    },
    "患者台词": "我平时不太好请假，参加这个研究需要经常来医院吗？",
    "是否结束": False,
}

# age_band → 采样年龄区间（闭区间）；具体岁数由模型在区间内选定并与其它设定一致
AGE_BAND_RANGES: dict[str, tuple[int, int]] = {
    "young_work": (25, 40),
    "mid": (41, 55),
    "elder": (60, 75),
}

HEALTH_LITERACY_BY_EDU: dict[str, str] = {
    "low": "低",
    "mid": "中",
    "high": "中高",
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class OpeningConfig:
    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT
    skill_path: Path = _SKILL_PATH
    trust_env: bool = True

    @classmethod
    def from_env(cls, **overrides: Any) -> OpeningConfig:
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
                os.getenv("ARK_OPENING_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "max_tokens": int(
                os.getenv("ARK_OPENING_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
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
class OpeningResult:
    data: dict[str, Any] = field(default_factory=dict)
    persona: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.data


# ---------------------------------------------------------------------------
# Persona helpers
# ---------------------------------------------------------------------------
def sample_patient_features(*, seed: int | None = None) -> dict[str, Any]:
    """每次开局前调用：从 service.agent.personality 随机采样患者特征。"""
    from service.agent.personality import sample_persona

    persona = sample_persona(seed=seed)
    logger.info(
        "personality.sample_persona seed=%s → %s",
        persona.seed,
        persona.render(),
    )
    return persona.to_dict()


def load_persona(
    path: Path | str | dict[str, Any] | None = None,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """加载人设 JSON；未提供路径时调用 sample_patient_features()。"""
    if isinstance(path, dict):
        return path
    if path is not None:
        p = Path(path)
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"患者特征 JSON 必须是对象: {p}")
            return data

    return sample_patient_features(seed=seed)


def persona_lock_card(persona: dict[str, Any]) -> dict[str, Any]:
    """把程序人设转成「不得修改」的中文约束卡，供模型遵守。"""
    from service.agent.personality import (
        AGE_BAND_LABELS,
        COMPANION_LABELS,
        DECISION_ROLE_LABELS,
        EDUCATION_LABELS,
        EMOTION_BASE_LABELS,
        LIFE_CONSTRAINT_LABELS,
        PRESSURE_LABELS,
        TRIAL_EXPERIENCE_LABELS,
    )

    age_band = str(persona.get("age_band", "mid"))
    education = str(persona.get("education", "mid"))
    constraints = persona.get("life_constraints") or []
    if isinstance(constraints, str):
        constraints = [constraints]

    lo, hi = AGE_BAND_RANGES.get(age_band, (35, 55))
    return {
        "年龄段代码": age_band,
        "年龄段标签": AGE_BAND_LABELS.get(age_band, age_band),
        "年龄取值范围": f"{lo}-{hi}岁（请在此区间内选一个整数写入画像.年龄）",
        "学历代码": education,
        "学历表述": EDUCATION_LABELS.get(education, education),
        "健康信息理解能力建议": HEALTH_LITERACY_BY_EDU.get(education, "中"),
        "试验经历代码": persona.get("trial_experience"),
        "试验经历表述": TRIAL_EXPERIENCE_LABELS.get(
            str(persona.get("trial_experience", "")),
            str(persona.get("trial_experience", "")),
        ),
        "情绪基调": EMOTION_BASE_LABELS.get(
            str(persona.get("emotion_base", "")),
            str(persona.get("emotion_base", "")),
        ),
        "决策角色": DECISION_ROLE_LABELS.get(
            str(persona.get("decision_role", "")),
            str(persona.get("decision_role", "")),
        ),
        "陪同": COMPANION_LABELS.get(
            str(persona.get("companion", "")),
            str(persona.get("companion", "")),
        ),
        "生活限制": [
            LIFE_CONSTRAINT_LABELS.get(str(c), str(c)) for c in constraints
        ],
        "训练压力": PRESSURE_LABELS.get(
            str(persona.get("pressure", "mid")),
            str(persona.get("pressure", "mid")),
        ),
        "seed": persona.get("seed"),
    }


def load_json_file(path: Path | str) -> Any:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_skill(path: Path | None = None) -> str:
    p = path or _SKILL_PATH
    if not p.is_file():
        raise FileNotFoundError(f"技能说明不存在: {p}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"技能说明为空: {p}")
    return text


def build_system_prompt(skill: str) -> str:
    schema_text = json.dumps(OUTPUT_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return (
        "你是 CRC 沟通训练的开局编剧，负责生成虚构患者的入组前首次提问状态。\n"
        "请严格依据技能说明与用户输入，只输出一个 JSON 对象。\n\n"
        "【技能说明】\n"
        f"{skill.strip()}\n\n"
        "【任务】\n"
        "1. 根据研究背景、顾虑池、患者特征生成连贯的虚构患者背景。\n"
        "2. 不认定患者已经通过正式筛选。\n"
        "3. 从顾虑池选择 2—3 个主要顾虑。\n"
        "4. 生成初始对话状态。\n"
        "5. 根据其中一个顾虑，生成患者开场问题。\n\n"
        "已有患者特征不得随意修改；研究资料未知的内容不得编造。\n\n"
        "【输出 Schema 示例】\n"
        f"{schema_text}\n\n"
        "只输出 JSON，不要 markdown 代码块，不要其它说明。"
    )


def build_user_prompt(
    *,
    background: dict[str, Any],
    concerns: list[dict[str, Any]],
    persona_lock: dict[str, Any],
) -> str:
    return (
        "请生成开局状态 JSON。\n\n"
        "【研究背景】\n"
        f"{json.dumps(background, ensure_ascii=False, indent=2)}\n\n"
        "【顾虑池】\n"
        f"{json.dumps(concerns, ensure_ascii=False, indent=2)}\n\n"
        "【程序选定的患者特征（不得随意修改，请映射到患者画像）】\n"
        f"{json.dumps(persona_lock, ensure_ascii=False, indent=2)}"
    )


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def parse_opening_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise ValueError("模型返回为空")
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
    raise ValueError(f"无法解析开局 JSON: {last_err}; 前200字={raw[:200]!r}")


def _str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_opening(
    data: dict[str, Any],
    *,
    persona: dict[str, Any],
    concern_topics: list[str],
    disease: str = "",
    raw_text: str = "",
    raw: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> OpeningResult:
    """规整输出；锁定筛选状态，校正主要顾虑属于顾虑池。"""
    from service.agent.personality import (
        COMPANION_LABELS,
        DECISION_ROLE_LABELS,
        EDUCATION_LABELS,
        EMOTION_BASE_LABELS,
        LIFE_CONSTRAINT_LABELS,
        PRESSURE_LABELS,
        TRIAL_EXPERIENCE_LABELS,
    )

    portrait_in = data.get("患者画像") if isinstance(data.get("患者画像"), dict) else {}
    state_in = data.get("状态") if isinstance(data.get("状态"), dict) else {}

    age_band = str(persona.get("age_band", "mid"))
    lo, hi = AGE_BAND_RANGES.get(age_band, (35, 55))
    try:
        age = int(portrait_in.get("年龄", (lo + hi) // 2))
    except (TypeError, ValueError):
        age = (lo + hi) // 2
    age = max(lo, min(hi, age))

    education = str(persona.get("education", "mid"))
    edu_short = {
        "low": "初中",
        "mid": "高中/大专",
        "high": "本科",
    }.get(education, EDUCATION_LABELS.get(education, education))

    companion_code = str(persona.get("companion", "alone"))
    companion_map = {
        "alone": "无",
        "spouse": "配偶",
        "adult_child": "成年子女",
    }
    companion = companion_map.get(
        companion_code,
        COMPANION_LABELS.get(companion_code, companion_code),
    )

    trial_code = str(persona.get("trial_experience", "naive"))
    trial_map = {
        "naive": "没有参加过",
        "prior": "曾参加过临床试验",
        "screen_failed_before": "曾筛败过",
    }
    trial = trial_map.get(
        trial_code,
        TRIAL_EXPERIENCE_LABELS.get(trial_code, trial_code),
    )

    decision_code = str(persona.get("decision_role", "self"))
    decision_map = {
        "self": "本人主导决策",
        "family_led": "想与家属商量",
        "self_vs_family": "想参加但需面对家属反对",
    }
    decision = decision_map.get(
        decision_code,
        DECISION_ROLE_LABELS.get(decision_code, decision_code),
    )

    emotion_code = str(persona.get("emotion_base", "hesitant"))
    emotion_label = EMOTION_BASE_LABELS.get(emotion_code, emotion_code)
    pressure_code = str(persona.get("pressure", "mid"))
    pressure_label = PRESSURE_LABELS.get(pressure_code, pressure_code)
    style_map = {
        "anxious": "紧张，反复确认",
        "hesitant": "谨慎，主动提问",
        "skeptical": "怀疑，追问依据",
        "pragmatic": "务实，关注费用与流程",
        "eager": "急切，希望尽快推进",
    }
    talk_style = style_map.get(emotion_code, "愿意提问")
    if pressure_code == "high":
        talk_style = f"{talk_style}（压力偏高）"
    elif pressure_code == "low":
        talk_style = f"{talk_style}（压力偏低）"

    emotion_state_map = {
        "anxious": "焦虑不安",
        "hesitant": "有些犹豫",
        "skeptical": "半信半疑",
        "pragmatic": "务实冷静",
        "eager": "急切求治",
    }
    emotion_state = emotion_state_map.get(emotion_code, "有些犹豫")

    constraints = persona.get("life_constraints") or []
    if isinstance(constraints, str):
        constraints = [constraints]
    life = [LIFE_CONSTRAINT_LABELS.get(str(c), str(c)) for c in constraints]

    disease_bg = str(portrait_in.get("疾病背景", "") or "").strip()
    if not disease_bg and disease:
        disease_bg = f"自述与{disease}相关不适，具体病史待询问"

    # 程序采样的人设字段强制锁定，不允许模型覆盖
    portrait = {
        "年龄": age,
        "学历": edu_short,
        "健康信息理解能力": HEALTH_LITERACY_BY_EDU.get(education, "中"),
        "试验经历": trial,
        "交流特点": talk_style,
        "决策偏好": decision,
        "陪同者": companion,
        "生活限制": life,
        "疾病背景": disease_bg,
        "筛选状态": "尚未正式筛选",
        "情绪基调": emotion_label,
        "压力水平": pressure_label,
    }

    pool_set = {t.strip() for t in concern_topics if t.strip()}
    main = _str_list(state_in.get("主要顾虑"))
    if pool_set:
        main = [t for t in main if t in pool_set] or list(pool_set)[:2]
    main = main[:3]
    if len(main) < 2 and pool_set:
        for t in concern_topics:
            if t not in main:
                main.append(t)
            if len(main) >= 2:
                break

    current = str(state_in.get("当前话题", "") or "").strip()
    if current not in main and main:
        current = main[0]

    state = {
        "主要顾虑": main,
        "当前话题": current,
        "已理解": _str_list(state_in.get("已理解")),
        "尚不清楚": _str_list(state_in.get("尚不清楚")),
        "待核实事项": _str_list(state_in.get("待核实事项")),
        "已讨论清楚的话题": _str_list(state_in.get("已讨论清楚的话题")),
        "当前情绪": emotion_state,
        "参与态度": str(state_in.get("参与态度", "") or "").strip() or "愿意了解",
    }

    line = str(data.get("患者台词", "") or "").strip()
    if not line:
        line = "我想先了解一下，参加这个研究大概是怎么回事？"

    out = {
        "患者画像": portrait,
        "状态": state,
        "患者台词": line,
        "是否结束": False,
    }
    return OpeningResult(
        data=out,
        persona=persona,
        raw_text=raw_text,
        raw=raw or {},
        usage=usage or {},
    )


def default_output_path(background_path: Path, out_dir: Path) -> Path:
    stem = background_path.stem
    if stem.endswith(".background"):
        stem = stem[: -len(".background")]
    return out_dir / f"{stem}.opening.json"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class OpeningQuestionAgent:
    def __init__(
        self,
        config: OpeningConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config or OpeningConfig.from_env()
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

    async def __aenter__(self) -> OpeningQuestionAgent:
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
                "OpeningQuestionAgent 未初始化：请使用 "
                "`async with OpeningQuestionAgent(...)`"
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
        concerns: Path | str | list[dict[str, Any]],
        persona: Path | str | dict[str, Any] | None = None,
        persona_seed: int | None = None,
    ) -> OpeningResult:
        """生成开局状态。

        每次调用都会先执行 ``service.agent.personality.sample_persona``，
        再将采样结果（或显式传入的人设）写入提示词。
        """
        bg = (
            background
            if isinstance(background, dict)
            else load_json_file(background)
        )
        if not isinstance(bg, dict):
            raise ValueError("研究背景必须是 JSON 对象")

        if isinstance(concerns, list):
            pool = concerns
        else:
            loaded = load_json_file(concerns)
            if not isinstance(loaded, list):
                raise ValueError("顾虑池必须是 JSON 数组")
            pool = loaded

        # 每次开局前先采样患者特征（程序选定）；仅当显式传入 persona 时覆盖
        sampled = sample_patient_features(seed=persona_seed)
        if persona is None:
            persona_dict = sampled
        else:
            persona_dict = load_persona(persona, seed=persona_seed)
            logger.info(
                "已用显式 persona 覆盖本次 sample_persona 结果（seed=%s）",
                sampled.get("seed"),
            )

        lock = persona_lock_card(persona_dict)
        topics = [
            str(x.get("话题", "")).strip()
            for x in pool
            if isinstance(x, dict) and str(x.get("话题", "")).strip()
        ]

        messages = [
            {"role": "system", "content": build_system_prompt(self.skill)},
            {
                "role": "user",
                "content": build_user_prompt(
                    background=bg,
                    concerns=pool,
                    persona_lock=lock,
                ),
            },
        ]
        text, raw, usage = await self._chat(messages)
        parsed = parse_opening_json(text)
        result = normalize_opening(
            parsed,
            persona=persona_dict,
            concern_topics=topics,
            disease=str(bg.get("疾病", "") or ""),
            raw_text=text,
            raw=raw,
            usage=usage,
        )
        result.persona = persona_dict
        return result


async def generate_opening(
    *,
    background: Path | str | dict[str, Any],
    concerns: Path | str | list[dict[str, Any]],
    persona: Path | str | dict[str, Any] | None = None,
    persona_seed: int | None = None,
    config: OpeningConfig | None = None,
) -> OpeningResult:
    async with OpeningQuestionAgent(config) as agent:
        return await agent.generate(
            background=background,
            concerns=concerns,
            persona=persona,
            persona_seed=persona_seed,
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="入组前首次提问 / 开局状态生成")
    p.add_argument(
        "--study",
        default=_DEFAULT_STUDY,
        help=f"研究 stem（默认 {_DEFAULT_STUDY}）；决定默认 -b/-c/-o",
    )
    p.add_argument(
        "--background",
        "-b",
        default=None,
        help="研究背景 JSON",
    )
    p.add_argument(
        "--concerns",
        "-c",
        default=None,
        help="顾虑池 JSON",
    )
    p.add_argument(
        "--persona",
        "-p",
        default=None,
        help="可选：覆盖人设的 JSON；默认每次先调用 personality.sample_persona()",
    )
    p.add_argument("--seed", type=int, default=None, help="传给 sample_persona 的随机种子")
    p.add_argument("--output", "-o", default=None, help="输出路径")
    p.add_argument("--out-dir", default=str(_DEFAULT_OUT_DIR))
    p.add_argument("--no-proxy", action="store_true")
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
    bg_path = Path(args.background) if args.background else paths.background
    concerns_path = Path(args.concerns) if args.concerns else paths.concerns
    out_path = Path(args.output) if args.output else paths.opening

    config = OpeningConfig.from_env(trust_env=False if args.no_proxy else None)
    try:
        config.require_api_key()
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if not bg_path.is_file():
        print(f"[FAIL] 研究背景不存在: {bg_path}", file=sys.stderr)
        return 1
    if not concerns_path.is_file():
        print(f"[FAIL] 顾虑池不存在: {concerns_path}", file=sys.stderr)
        return 1
    if args.persona and not Path(args.persona).is_file():
        print(f"[FAIL] 患者特征不存在: {args.persona}", file=sys.stderr)
        return 1

    try:
        async with OpeningQuestionAgent(config) as agent:
            result = await agent.generate(
                background=bg_path,
                concerns=concerns_path,
                persona=args.persona,
                persona_seed=args.seed,
            )
    except httpx.ConnectError as exc:
        print(
            "[FAIL] 无法连接方舟 API。可加 --no-proxy 直连。\n"
            f"详情: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "[persona] "
        + json.dumps(result.persona, ensure_ascii=False, default=str),
        file=sys.stderr,
    )
    text = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"wrote {out_path} model={config.model}", file=sys.stderr)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain(sys.argv[1:])))


if __name__ == "__main__":
    main()
