"""Build a LiveKit patient system prompt from a CRC DialogueSession.

medkit's voice worker (Deepgram → Haiku → Cartesia) reads `systemPrompt`
from room metadata. CRC keeps structured PatientTurn state for text turns;
for voice we compress that state into instructions so the spoken patient
stays in-character. Transcripts are synced back after the call for scoring.
"""

from __future__ import annotations

import json
from typing import Any


def _clip(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _concern_lines(concerns: list[Any], *, limit: int = 12) -> str:
    lines: list[str] = []
    for item in concerns[:limit]:
        if isinstance(item, dict):
            topic = str(item.get("话题") or item.get("topic") or "").strip()
            q = str(item.get("典型问法") or item.get("question") or item.get("顾虑") or "").strip()
            if topic and q:
                lines.append(f"- {topic}：{q}")
            elif topic:
                lines.append(f"- {topic}")
            elif q:
                lines.append(f"- {q}")
        elif item:
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else "- （顾虑池为空）"


def _bg_summary(background: dict[str, Any]) -> str:
    preferred_keys = (
        "研究名称",
        "适应症",
        "试验分期",
        "干预",
        "对照",
        "主要终点",
        "关键安排摘要",
        "未提供的信息",
        "title",
        "indication",
        "summary",
    )
    parts: list[str] = []
    for key in preferred_keys:
        if key in background and background[key] not in (None, "", [], {}):
            val = background[key]
            if isinstance(val, (dict, list)):
                parts.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
            else:
                parts.append(f"{key}: {val}")
    if not parts:
        # Fallback: compact dump of a few top-level fields
        for key, val in list(background.items())[:8]:
            if isinstance(val, (dict, list)):
                parts.append(f"{key}: {_clip(json.dumps(val, ensure_ascii=False), 240)}")
            else:
                parts.append(f"{key}: {val}")
    return _clip("\n".join(parts), 1600)


def build_crc_voice_prompt(
    *,
    study_stem: str,
    background: dict[str, Any],
    concerns: list[Any],
    portrait: dict[str, Any],
    state: dict[str, Any] | None = None,
    recent_dialogue: list[dict[str, str]] | None = None,
) -> str:
    """Instructions for the LiveKit patient agent (spoken Chinese)."""
    portrait_json = json.dumps(portrait, ensure_ascii=False, indent=2)
    state_json = json.dumps(state or {}, ensure_ascii=False, indent=2)
    history = ""
    if recent_dialogue:
        tail = recent_dialogue[-8:]
        history = "\n".join(
            f"{'患者' if m.get('role') == 'patient' else 'CRC'}：{m.get('content', '')}"
            for m in tail
        )

    return f"""你是一名正在与临床研究协调员（CRC）进行「入组前知情沟通」的患者（或陪同家属）。
用自然口语中文说话，每次只说 1～2 句短话，适合语音朗读。
不要输出舞台指示、星号、括号旁白或 JSON。

研究：{study_stem}

【患者画像】（必须保持一致，不得改成相反设定）
{portrait_json}

【当前理解状态】
{state_json}

【研究背景（可知范围；未列出的细节你不知道）】
{_bg_summary(background)}

【可能关心的话题 / 顾虑】
{_concern_lines(concerns)}

【近期对话】
{history or "（刚开始）"}

硬性规则：
1. 只扮演患者；CRC 是对方。
2. 不知道的研究细节不要编造数字或安排；可以说「这个我还不清楚」或继续追问。
3. 若 CRC 刚问了你问题，先简短回答，再视情况追问或表态。
4. 不要原样重复上一句；每句都要对 CRC 刚说的话有反应。
5. 情绪与交流特点贴合画像；可以犹豫、担心、想回去和家属商量。
6. 准备结束时可说：暂时没问题了 / 回去商量 / 等你们核实后再联系 / 暂时不考虑。
"""


def gender_from_portrait(portrait: dict[str, Any]) -> str:
    """Map CRC portrait fields to medkit voice gender 'M'|'F'."""
    raw = str(
        portrait.get("性别")
        or portrait.get("gender")
        or portrait.get("sex")
        or ""
    ).strip().upper()
    if raw in {"F", "女", "FEMALE", "WOMAN"}:
        return "F"
    if raw in {"M", "男", "MALE", "MAN"}:
        return "M"
    # Default: slightly prefer female Cartesia slots for CRC training voices
    return "F"


def initial_line_from_session(
    *,
    last_line: str,
    dialogue: list[dict[str, str]],
) -> str:
    if last_line.strip():
        return last_line.strip()
    for m in reversed(dialogue):
        if m.get("role") == "patient" and str(m.get("content") or "").strip():
            return str(m["content"]).strip()
    return "你好，我想了解一下这个试验。"
