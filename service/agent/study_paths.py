"""CRC 训练流水线 — 按研究 stem 解析统一产物路径。

默认研究与 opening / patient_turn 对齐，避免各 CLI 默认病种不一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
ACK = SERVICE_ROOT / "acknowledge"

# 与 opening_question / patient_turn 历史默认一致
DEFAULT_STUDY = "Chronic rhinosinusitis with nasal polyps"

DEFAULT_TRAINING = ACK / "crc_pre_enrollment_dialogue.md"
FALLBACK_TRAINING = ACK / "crc_interview.md"


@dataclass(frozen=True)
class StudyPaths:
    stem: str
    cde_json: Path
    background: Path
    concerns: Path
    opening: Path
    training: Path
    sessions_dir: Path

    def ensure_parent_dirs(self) -> None:
        for p in (self.background, self.concerns, self.opening):
            p.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


def normalize_stem(stem: str) -> str:
    s = stem.strip()
    for suffix in (".background", ".concerns", ".opening"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    if s.endswith(".json"):
        s = s[: -len(".json")]
    return s


def resolve_training(path: Path | None = None) -> Path:
    if path is not None:
        return path
    if DEFAULT_TRAINING.is_file():
        return DEFAULT_TRAINING
    return FALLBACK_TRAINING


def resolve_study(stem: str | None = None) -> StudyPaths:
    name = normalize_stem(stem or DEFAULT_STUDY)
    return StudyPaths(
        stem=name,
        cde_json=ACK / "relative_experiment" / f"{name}.json",
        background=ACK / "relative_experiment" / f"{name}.background.json",
        concerns=ACK / "questions_pool" / f"{name}.concerns.json",
        opening=ACK / "opening_state" / f"{name}.opening.json",
        training=resolve_training(),
        sessions_dir=ACK / "dialogue_sessions",
    )


def list_known_studies() -> list[str]:
    """列出已有 CDE JSON（不含 .background.json）。"""
    root = ACK / "relative_experiment"
    if not root.is_dir():
        return []
    stems: list[str] = []
    for p in sorted(root.glob("*.json")):
        if p.name.endswith(".background.json"):
            continue
        stems.append(p.stem)
    return stems
