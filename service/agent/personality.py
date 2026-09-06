"""CRC 沟通训练 — 患者人设维度与开局随机采样。

每次启动 / 开局调用 `sample_persona()`，从闭集枚举中随机抽取一套人设。
`life_constraints` 为多选（随机抽取 0～全部子集）。
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from typing import Sequence

# ---------------------------------------------------------------------------
# 维度可选值（闭集）
# ---------------------------------------------------------------------------

AGE_BANDS: tuple[str, ...] = ("young_work", "mid", "elder")

EDUCATIONS: tuple[str, ...] = ("low", "mid", "high")
EDUCATION_LABELS: dict[str, str] = {
    "low": "初中及以下",
    "mid": "高中大专",
    "high": "本科及以上",
}

TRIAL_EXPERIENCES: tuple[str, ...] = (
    "naive",
    "prior",
    "screen_failed_before",
)
TRIAL_EXPERIENCE_LABELS: dict[str, str] = {
    "naive": "首次参加临床试验",
    "prior": "曾参加过临床试验",
    "screen_failed_before": "曾筛败过",
}

EMOTION_BASES: tuple[str, ...] = (
    "anxious",
    "hesitant",
    "skeptical",
    "pragmatic",
    "eager",
)
EMOTION_BASE_LABELS: dict[str, str] = {
    "anxious": "焦虑",
    "hesitant": "犹豫",
    "skeptical": "怀疑（小白鼠感）",
    "pragmatic": "务实（偏费用/流程）",
    "eager": "急切求治",
}

DECISION_ROLES: tuple[str, ...] = ("self", "family_led", "self_vs_family")
DECISION_ROLE_LABELS: dict[str, str] = {
    "self": "本人主导决策",
    "family_led": "家属主导决策",
    "self_vs_family": "本人想参加但家属反对",
}

COMPANIONS: tuple[str, ...] = ("alone", "spouse", "adult_child")
COMPANION_LABELS: dict[str, str] = {
    "alone": "独自沟通",
    "spouse": "配偶陪同",
    "adult_child": "成年子女陪同",
}

LIFE_CONSTRAINTS: tuple[str, ...] = (
    "hard_to_leave_work",
    "long_distance",
    "money_sensitive",
    "chronic_comorbid",
)
LIFE_CONSTRAINT_LABELS: dict[str, str] = {
    "hard_to_leave_work": "工作日难请假",
    "long_distance": "路途远",
    "money_sensitive": "经济敏感",
    "chronic_comorbid": "合并慢病",
}

PRESSURES: tuple[str, ...] = ("low", "mid", "high")
PRESSURE_LABELS: dict[str, str] = {
    "low": "低压力",
    "mid": "中压力",
    "high": "高压力",
}

AGE_BAND_LABELS: dict[str, str] = {
    "young_work": "青年上班族",
    "mid": "中年",
    "elder": "老年",
}


# ---------------------------------------------------------------------------
# 人设结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Persona:
    """一次会话开局固定的患者人设。"""

    age_band: str
    education: str
    trial_experience: str
    emotion_base: str
    decision_role: str
    companion: str
    life_constraints: tuple[str, ...] = field(default_factory=tuple)
    pressure: str = "mid"
    seed: int | None = None

    def label(self, field_name: str, code: str) -> str:
        tables: dict[str, dict[str, str]] = {
            "age_band": AGE_BAND_LABELS,
            "education": EDUCATION_LABELS,
            "trial_experience": TRIAL_EXPERIENCE_LABELS,
            "emotion_base": EMOTION_BASE_LABELS,
            "decision_role": DECISION_ROLE_LABELS,
            "companion": COMPANION_LABELS,
            "life_constraints": LIFE_CONSTRAINT_LABELS,
            "pressure": PRESSURE_LABELS,
        }
        return tables.get(field_name, {}).get(code, code)

    def render(self) -> str:
        """拼成可写入 ScenarioSpec / system prompt 的中文人设描述。"""
        constraints = "、".join(
            self.label("life_constraints", c) for c in self.life_constraints
        )
        if not constraints:
            constraints = "无明显额外生活约束"

        return (
            f"{self.label('age_band', self.age_band)}，"
            f"文化程度{self.label('education', self.education)}，"
            f"{self.label('trial_experience', self.trial_experience)}，"
            f"情绪基调：{self.label('emotion_base', self.emotion_base)}，"
            f"决策：{self.label('decision_role', self.decision_role)}，"
            f"陪同：{self.label('companion', self.companion)}，"
            f"约束：{constraints}，"
            f"训练压力：{self.label('pressure', self.pressure)}"
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sample_life_constraints(
    rng: random.Random,
    *,
    pool: Sequence[str] = LIFE_CONSTRAINTS,
    max_k: int | None = None,
) -> tuple[str, ...]:
    """多选：随机抽取 0～len(pool) 个约束（打乱后取前 k）。"""
    items = list(pool)
    if not items:
        return ()
    upper = len(items) if max_k is None else min(max_k, len(items))
    k = rng.randint(0, upper)
    if k == 0:
        return ()
    return tuple(rng.sample(items, k=k))


def sample_persona(
    *,
    seed: int | None = None,
    max_constraints: int | None = None,
) -> Persona:
    """每次调用随机生成一套人设；传入 seed 可复现。"""
    rng = random.Random(seed)
    resolved_seed = seed if seed is not None else rng.randint(0, 2**31 - 1)
    # 未指定 seed 时仍写入一个可读 seed，便于日志复现本局
    if seed is None:
        rng = random.Random(resolved_seed)

    return Persona(
        age_band=rng.choice(AGE_BANDS),
        education=rng.choice(EDUCATIONS),
        trial_experience=rng.choice(TRIAL_EXPERIENCES),
        emotion_base=rng.choice(EMOTION_BASES),
        decision_role=rng.choice(DECISION_ROLES),
        companion=rng.choice(COMPANIONS),
        life_constraints=_sample_life_constraints(
            rng, max_k=max_constraints
        ),
        pressure=rng.choice(PRESSURES),
        seed=resolved_seed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="随机采样患者人设维度")
    parser.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    parser.add_argument(
        "--max-constraints",
        type=int,
        default=None,
        help="生活约束最多抽取个数（默认 0～全部）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args(list(argv) if argv is not None else None)

    persona = sample_persona(seed=args.seed, max_constraints=args.max_constraints)
    if args.json:
        print(json.dumps(persona.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"seed={persona.seed}")
        print(persona.render())
        print("---")
        for key, value in persona.to_dict().items():
            if key == "seed":
                continue
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
