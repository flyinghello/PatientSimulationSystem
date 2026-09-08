"""能力画像与下一轮定向选题推荐。

数据来源：
- 用户历史训练记录（training_records.json 中该用户的记录）；
- 病例目录（service/acknowledge/study_catalog.json，含 focus_dimensions 能力标签）。

推荐逻辑（老师要求的「第二次与第一次不同、每次针对薄弱项提升」）：
1. 无任何记录 → 推荐目录第一项，目标为「建立基线」；
2. 存在薄弱维度（平均分 < 75）→ 优先推荐能覆盖薄弱维度的、
   且用户练得最少的病例；
3. 各维度均已达标 → 推荐练得最少的病例，拓展场景广度。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "acknowledge" / "study_catalog.json"

WEAK_THRESHOLD = 75.0
STRONG_THRESHOLD = 85.0


def load_study_catalog(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or _CATALOG_PATH
    if not p.is_file():
        return []
    try:
        data = __import__("json").loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("studies", data) if isinstance(data, dict) else data
    return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []


def _dimension_scores(records: list[dict[str, Any]]) -> dict[str, float]:
    """按维度名聚合历史记录的平均分（0~100）。"""
    acc: dict[str, list[float]] = {}
    for rec in records:
        for d in rec.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = str(d.get("dimension") or "").strip()
            score = d.get("score")
            if not dim or not isinstance(score, (int, float)):
                continue
            acc.setdefault(dim, []).append(float(score))
    return {
        dim: round(sum(scores) / len(scores), 1) for dim, scores in acc.items()
    }


def compute_profile(records: list[dict[str, Any]]) -> dict[str, Any]:
    """计算用户能力画像：维度均分、优势、薄弱项、总体指标。"""
    dims = _dimension_scores(records)
    weaknesses = sorted(
        (d for d, s in dims.items() if s < WEAK_THRESHOLD),
        key=lambda d: dims[d],
    )[:2]
    strengths = sorted(
        (d for d, s in dims.items() if s >= STRONG_THRESHOLD),
        key=lambda d: dims[d],
        reverse=True,
    )[:3]
    scores = [r.get("overall_score") for r in records if isinstance(r.get("overall_score"), (int, float))]
    return {
        "dimension_scores": dims,
        "weaknesses": [
            {"dimension": d, "score": dims[d]} for d in weaknesses
        ],
        "strengths": [
            {"dimension": d, "score": dims[d]} for d in strengths
        ],
        "total_sessions": len(records),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "pass_rate": (
            round(100.0 * sum(1 for r in records if r.get("passed")) / len(records), 1)
            if records
            else None
        ),
    }


def recommend_study(
    records: list[dict[str, Any]],
    catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """推荐下一轮训练的病例与训练目标。"""
    catalog = catalog if catalog is not None else load_study_catalog()
    profile = compute_profile(records)
    if not catalog:
        return {
            "study": None,
            "label": "",
            "reason": "暂无可用病例目录，请联系管理员上传临床试验。",
            "training_goal": "",
            "is_repeat": False,
            **profile,
        }

    practiced: dict[str, int] = {}
    for rec in records:
        study = str(rec.get("study") or "")
        if study:
            practiced[study] = practiced.get(study, 0) + 1

    weakness_dims = [w["dimension"] for w in profile["weaknesses"]]

    def _times(s: dict[str, Any]) -> int:
        return practiced.get(str(s.get("stem") or ""), 0)

    if not records:
        target = catalog[0]
        return {
            "study": target.get("stem"),
            "label": target.get("label") or target.get("stem"),
            "reason": "这是你的第一次训练，先完成基线评估。",
            "training_goal": "完成第一次入组前沟通训练，建立能力基线。",
            "is_repeat": False,
            **profile,
        }

    if weakness_dims:
        target = None
        for dim in weakness_dims:
            hit = [
                s for s in catalog
                if dim in (s.get("focus_dimensions") or [])
            ]
            if not hit:
                continue
            hit.sort(key=_times)
            target = hit[0]
            if target:
                break
        if target is None:
            target = sorted(catalog, key=_times)[0]
        reason = (
            f"你在「{weakness_dims[0]}」维度相对薄弱"
            f"（平均 {profile['dimension_scores'].get(weakness_dims[0])} 分），"
            "本病例专门强化该能力。"
        )
        goal = f"本回合重点练习：{weakness_dims[0]}。注意运用上次复盘给出的改进建议，并留意患者情绪与反馈。"
        return {
            "study": target.get("stem"),
            "label": target.get("label") or target.get("stem"),
            "reason": reason,
            "training_goal": goal,
            "is_repeat": practiced.get(str(target.get("stem") or ""), 0) > 0,
            **profile,
        }

    # 无薄弱项：拓展广度，练习最少的新病例
    target = sorted(catalog, key=_times)[0]
    return {
        "study": target.get("stem"),
        "label": target.get("label") or target.get("stem"),
        "reason": "各维度表现均衡，为你推荐一个接触较少的病例拓展场景。",
        "training_goal": "尝试新病例场景，保持各维度能力，关注信息传递的完整性。",
        "is_repeat": practiced.get(str(target.get("stem") or ""), 0) > 0,
        **profile,
    }
