"""把患者「当前情绪」映射到火山 TTS 官方 emotion 枚举。

文档要点（大模型语音合成 API · 多情感音色）：
- emotion 必须是音色支持的固定选项，不可随意字符串。
- 不同音色支持范围不同；见音色列表「多情感音色」。
- emotion_scale：1~5，默认 4。

当前默认音色 zh_female_gaolengyujie_emo_v2_mars_bigtts（高冷御姐）支持：
  happy / sad / angry / surprised / fear / hate / excited / coldness / neutral
对应中文：开心 / 悲伤 / 生气 / 惊讶 / 恐惧 / 厌恶 / 激动 / 冷漠 / 中性
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# 官方 emotion 英文码（按音色）
# 来源：火山「大模型语音合成API-音色列表-多情感音色」
# ---------------------------------------------------------------------------

SPEAKER_GAOLENG = "zh_female_gaolengyujie_emo_v2_mars_bigtts"
SPEAKER_ROUMEI = "zh_female_roumeinvyou_emo_v2_mars_bigtts"
SPEAKER_SHUANGKUAI_SISI = "zh_female_shuangkuaisisi_emo_v2_mars_bigtts"

EMOTIONS_SHUANGKUAI_SISI = frozenset(
    {"happy", "sad", "angry", "surprised", "excited", "coldness", "neutral"}
)

# 柔美女友 / 高冷御姐（更全，含 fear / hate）
EMOTIONS_FULL_FEMALE = frozenset(
    {
        "happy",
        "sad",
        "angry",
        "surprised",
        "fear",
        "hate",
        "excited",
        "coldness",
        "neutral",
    }
)

SPEAKER_EMOTIONS: dict[str, frozenset[str]] = {
    SPEAKER_GAOLENG: EMOTIONS_FULL_FEMALE,
    SPEAKER_ROUMEI: EMOTIONS_FULL_FEMALE,
    SPEAKER_SHUANGKUAI_SISI: EMOTIONS_SHUANGKUAI_SISI,
    "zh_male_yangguangqingnian_emo_v2_mars_bigtts": frozenset(
        {"happy", "sad", "angry", "fear", "excited", "coldness", "neutral"}
    ),
    "zh_male_beijingxiaoye_emo_v2_mars_bigtts": frozenset(
        {"angry", "surprised", "fear", "excited", "coldness", "neutral"}
    ),
}

DEFAULT_SPEAKER = SPEAKER_GAOLENG
DEFAULT_EMOTION = "neutral"
DEFAULT_EMOTION_SCALE = 4

# 中文官方标签 ↔ API 英文码（与文档表一致）
CN_TO_EN: dict[str, str] = {
    "开心": "happy",
    "悲伤": "sad",
    "生气": "angry",
    "惊讶": "surprised",
    "恐惧": "fear",
    "厌恶": "hate",
    "激动": "excited",
    "冷漠": "coldness",
    "中性": "neutral",
    "沮丧": "sad",
}

# LLM / 状态字段允许的中文枚举（与高冷御姐对齐）
PATIENT_EMOTION_CN = (
    "开心",
    "悲伤",
    "生气",
    "惊讶",
    "恐惧",
    "厌恶",
    "激动",
    "冷漠",
    "中性",
)

# 口语同义词 → 官方中文枚举（入组对话：勿把「犹豫」夸成「恐惧」）
_SYNONYM_TO_CN: tuple[tuple[tuple[str, ...], str], ...] = (
    (("愤怒", "生气", "恼火", "火大", "抗议", "angry"), "生气"),
    (("不满", "被敷衍"), "生气"),
    (("恐惧", "害怕", "惊恐", "恐慌", "吓人", "吓到", "fear"), "恐惧"),
    (("厌恶", "反感", "抵触", "排斥", "讨厌", "hate"), "厌恶"),
    (("失望", "难过", "伤心", "沮丧", "低落", "无奈", "sad"), "悲伤"),
    (("担心", "焦虑", "紧张", "不安", "忧虑", "忐忑"), "悲伤"),
    (("犹豫", "顾虑", "将信将疑", "半信半疑", "再想想", "不太敢"), "悲伤"),
    (("惊讶", "吃惊", "意外", "诧异", "surprised"), "惊讶"),
    (("兴奋", "激动", "振奋", "急切", "迫切", "着急", "催一下", "excited"), "激动"),
    (("高兴", "开心", "欣慰", "放心", "满意", "轻松", "释然", "乐观", "happy"), "开心"),
    (("冷淡", "冷漠", "敷衍", "无所谓", "麻木", "懒得", "coldness"), "冷漠"),
    (("平静", "冷静", "平和", "中性", "配合", "了解一下", "neutral"), "中性"),
)

# 从台词推断情绪（强信号优先；用于校正 LLM 乱标）
_LINE_HINTS: tuple[tuple[tuple[str, ...], str, int], ...] = (
    (("太过分", "骗人", "忽悠", "生气", "火大", "什么态度", "这什么态度", "尊重一点"), "生气", 3),
    (("反感", "不想听", "别说了", "不考虑了", "没兴趣", "被打发", "敷衍我"), "厌恶", 3),
    (("好怕", "害怕", "吓坏", "不敢参加", "会不会死", "很恐怖"), "恐惧", 3),
    (("放心多了", "明白了", "那就好", "谢谢您说清楚", "愿意了解"), "开心", 2),
    (("太意外", "没想到", "这么久", "这么贵"), "惊讶", 2),
    (("赶紧", "尽快", "催一下", "什么时候能定"), "激动", 2),
    (("算了", "随便吧", "你看着办", "无所谓"), "冷漠", 2),
    (("还是不放心", "还是担心", "有点失望", "无奈"), "悲伤", 2),
    # 谨慎追问：压过 LLM 乱标的「恐惧」（若 CRC 冷漠则另案处理）
    (("再确认", "再问问", "还想确认", "能不能再说", "我再想想", "想再了解", "方便再说"), "中性", 2),
)


# CRC 不尊重 / 冷漠话术 → 患者应生气或厌恶
_CRC_DISRESPECT_STRONG: tuple[str, ...] = (
    "你懂什么",
    "别问了",
    "少废话",
    "听不懂吗",
    "自己看",
    "关你什么事",
    "爱参加不参加",
    "不愿意就算了",
    "烦不烦",
    "有完没完",
    "啰嗦",
    "闭嘴",
    "懒得解释",
)
_CRC_COLD_HINTS: tuple[str, ...] = (
    "随便",
    "都行",
    "不知道",
    "不关我事",
    "你自己决定",
    "问别人去",
    "下次再说",
    "没空",
    "忙着呢",
    "就这样吧",
    "没什么好说的",
    "按规定来",
    "别多想",
    "想太多",
    "没必要问",
    "这个不用管",
    "你别管",
    "听安排就行",
    "签了就行",
    "快点",
    "赶紧签",
    "别耽误时间",
)


def classify_crc_attitude(crc_reply: str | None) -> str | None:
    """检测 CRC 话术态度。返回 '厌恶' | '生气' | None。"""
    text = (crc_reply or "").strip()
    if not text:
        return None
    if any(k in text for k in _CRC_DISRESPECT_STRONG):
        return "厌恶"
    if any(k in text for k in _CRC_COLD_HINTS):
        return "生气"
    # 极短敷衍（几乎不回答）
    compact = re.sub(r"\s+", "", text)
    if len(compact) <= 4 and compact in {
        "嗯", "哦", "行", "好", "知道了", "收到", "嗯嗯", "哦哦", "随便", "都行",
    }:
        return "生气"
    # 全是打发：只有「你自己看/问医生」类且无实质信息
    if len(compact) <= 12 and any(
        k in text for k in ("自己看", "问医生", "网上查", "说明书")
    ):
        return "生气"
    return None


def _looks_like_calm_followup(line: str) -> bool:
    """平静追问：有问号/疑问，且无强情绪词。"""
    if not line:
        return False
    if not any(x in line for x in ("？", "?", "吗", "呢", "能不能", "是不是", "要不要")):
        return False
    strong = (
        "怕", "恐", "怒", "火", "骗", "忽悠", "反感", "讨厌", "死", "放心多了", "太过分"
    )
    return not any(s in line for s in strong)


def infer_emotion_from_line(line: str | None) -> tuple[str | None, int]:
    """从患者台词抽情绪；无命中返回 (None, 0)。confidence 1~3。"""
    text = (line or "").strip()
    if not text:
        return None, 0
    best_cn: str | None = None
    best_score = 0
    for keys, cn, score in _LINE_HINTS:
        if any(k in text for k in keys) and score > best_score:
            best_cn, best_score = cn, score
    if best_cn is None and _looks_like_calm_followup(text):
        return "中性", 2
    return best_cn, best_score


def resolve_patient_emotion(
    llm_label: str | None,
    line: str | None = None,
    *,
    prev_label: str | None = None,
    crc_reply: str | None = None,
) -> str:
    """综合 LLM 标注、CRC 态度与台词语气，得到更准的「当前情绪」。"""
    # CRC 不尊重/冷漠：强制生气或厌恶（训练场景硬规则）
    crc_emo = classify_crc_attitude(crc_reply)
    if crc_emo:
        line_cn, conf = infer_emotion_from_line(line)
        # 台词已明确厌恶时保留厌恶；否则用 CRC 定的生气/厌恶
        if line_cn == "厌恶" and conf >= 2:
            return "厌恶"
        if line_cn == "生气" and conf >= 2:
            return "生气"
        return crc_emo

    llm_cn = normalize_patient_emotion_cn(llm_label or prev_label or "中性")
    line_cn, conf = infer_emotion_from_line(line)

    if line_cn is None:
        # LLM 标恐惧但台词像平静追问
        if llm_cn in ("恐惧", "厌恶", "激动") and _looks_like_calm_followup(line or ""):
            return "中性"
        return llm_cn

    # 台词强信号：覆盖模糊/夸张的 LLM 标注
    if conf >= 2:
        if llm_cn in ("恐惧", "厌恶", "激动") and line_cn in ("中性", "悲伤", "开心"):
            return line_cn
        if llm_cn in ("中性", "冷漠") and line_cn != llm_cn:
            return line_cn
        opposing = {
            "开心": {"生气", "悲伤", "厌恶", "恐惧"},
            "生气": {"开心", "中性"},
            "悲伤": {"开心"},
            "厌恶": {"开心"},
            "恐惧": {"开心", "中性"},
        }
        if line_cn in opposing.get(llm_cn, set()):
            return line_cn
        if conf >= 3:
            return line_cn

    return llm_cn


def allowed_emotions(speaker: str | None = None) -> frozenset[str]:
    sp = (speaker or DEFAULT_SPEAKER).strip()
    return SPEAKER_EMOTIONS.get(sp, EMOTIONS_FULL_FEMALE)


def clamp_emotion(
    emotion: str | None,
    *,
    speaker: str | None = None,
    fallback: str = DEFAULT_EMOTION,
) -> str:
    """只允许当前音色支持的官方 emotion；非法则回退。"""
    allowed = allowed_emotions(speaker)
    emo = (emotion or "").strip().lower()
    if emo in allowed:
        return emo
    # 不支持的常见码 → 近似回退（仍须在 allowed 内）
    remap = {
        "fear": "sad",
        "hate": "angry",
        "depressed": "sad",
        "scare": "fear" if "fear" in allowed else "sad",
        "pleased": "happy",
        "sorry": "sad",
        "annoyed": "angry",
        "surprise": "surprised",
    }
    alt = remap.get(emo)
    if alt and alt in allowed:
        return alt
    if fallback in allowed:
        return fallback
    return next(iter(allowed))


def normalize_patient_emotion_cn(label: str | None) -> str:
    """把自由文本收成 PATIENT_EMOTION_CN 之一。"""
    text = (label or "").strip()
    if not text:
        return "中性"
    if text in PATIENT_EMOTION_CN:
        return text
    # 已是英文码
    lower = text.lower()
    for cn, en in CN_TO_EN.items():
        if lower == en and cn in PATIENT_EMOTION_CN:
            return cn
    for keys, cn in _SYNONYM_TO_CN:
        if any(k in text for k in keys):
            return cn if cn in PATIENT_EMOTION_CN else "中性"
    return "中性"


def map_emotion_label(
    label: str | None,
    *,
    speaker: str | None = None,
    default: str = DEFAULT_EMOTION,
) -> tuple[str, int]:
    """中文/英文情绪描述 → (官方 emotion 英文码, scale 1~5)。"""
    text = (label or "").strip()
    scale = DEFAULT_EMOTION_SCALE
    if not text:
        return clamp_emotion(default, speaker=speaker), scale

    lower = text.lower()
    allowed = allowed_emotions(speaker)
    if lower in allowed:
        return lower, scale

    # 官方中文标签
    if text in CN_TO_EN:
        return clamp_emotion(CN_TO_EN[text], speaker=speaker), scale

    cn = normalize_patient_emotion_cn(text)
    en = CN_TO_EN.get(cn, default)
    # 略调强度：入组对话偏克制，避免整段都「撕心裂肺」
    if cn in ("生气", "厌恶"):
        scale = 5
    elif cn == "恐惧":
        scale = 4
    elif cn == "激动":
        scale = 4
    elif cn in ("开心", "惊讶", "悲伤"):
        scale = 3
    elif cn == "中性":
        scale = 2
    elif cn == "冷漠":
        scale = 3
    return clamp_emotion(en, speaker=speaker, fallback=default), scale


def emotion_from_session_state(
    state: dict[str, Any] | None,
    portrait: dict[str, Any] | None = None,
    *,
    speaker: str | None = None,
    line: str | None = None,
    crc_reply: str | None = None,
) -> tuple[str, int]:
    """优先用状态.当前情绪（可结合台词/CRC 态度校正），否则画像.情绪基调。"""
    label = ""
    if isinstance(state, dict):
        label = str(state.get("当前情绪") or "").strip()
    if line or crc_reply:
        label = resolve_patient_emotion(label, line, crc_reply=crc_reply)
    elif not label and isinstance(portrait, dict):
        label = str(portrait.get("情绪基调") or portrait.get("交流特点") or "").strip()
    return map_emotion_label(label, speaker=speaker)
