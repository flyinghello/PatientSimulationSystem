"""CRC 训练流水线编排：按 --study 串联各阶段 CLI。

示例：
  python service/agent/run_pipeline.py --study "Chronic rhinosinusitis with nasal polyps" --stages prep
  python service/agent/run_pipeline.py --study "B-cell malignancies" --stages opening
  python service/agent/run_pipeline.py --stages turn --interactive
  python service/agent/run_pipeline.py --stages evaluate --session service/acknowledge/dialogue_sessions/session_xxx
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from service.agent.study_paths import (  # noqa: E402
    DEFAULT_STUDY,
    list_known_studies,
    resolve_study,
)

STAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "prep": ("background", "concerns", "opening"),
    "all": ("background", "concerns", "opening", "turn", "evaluate"),
}

VALID_STAGES = ("background", "concerns", "opening", "turn", "evaluate")


def _expand_stages(raw: Sequence[str]) -> list[str]:
    out: list[str] = []
    for token in raw:
        key = token.strip().lower()
        if key in STAGE_ALIASES:
            out.extend(STAGE_ALIASES[key])
        elif key in VALID_STAGES:
            out.append(key)
        else:
            raise ValueError(
                f"未知阶段 {token!r}；可选: {', '.join(VALID_STAGES)} "
                f"或别名 prep/all"
            )
    # 保序去重
    seen: set[str] = set()
    ordered: list[str] = []
    for s in out:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="按研究 stem 编排 CRC agent 流水线",
    )
    p.add_argument(
        "--study",
        default=DEFAULT_STUDY,
        help=f"研究 stem（默认 {DEFAULT_STUDY}）",
    )
    p.add_argument(
        "--stages",
        nargs="+",
        default=["prep"],
        help="阶段：background concerns opening turn evaluate；别名 prep / all",
    )
    p.add_argument("--seed", type=int, default=None, help="开局人设采样种子")
    p.add_argument(
        "--session",
        default=None,
        help="turn/evaluate 使用的会话目录",
    )
    p.add_argument(
        "--crc",
        default=None,
        help="turn 单轮：CRC 回复文本",
    )
    p.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="turn 交互模式",
    )
    p.add_argument("--trainee", default=None, help="evaluate 受训 CRC 姓名")
    p.add_argument("--scenario", default=None, help="evaluate 情景描述")
    p.add_argument("--no-proxy", action="store_true")
    p.add_argument("--list-studies", action="store_true", help="列出已知研究 stem")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def _common_flags(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if args.no_proxy:
        flags.append("--no-proxy")
    if args.verbose:
        flags.append("-v")
    return flags


async def _run_background(args: argparse.Namespace, paths) -> int:
    from service.agent import experiment_background as mod

    argv = [
        "--study",
        paths.stem,
        "-i",
        str(paths.cde_json),
        "-o",
        str(paths.background),
        *_common_flags(args),
    ]
    return await mod._amain(argv)


async def _run_concerns(args: argparse.Namespace, paths) -> int:
    from service.agent import concern_pool as mod

    argv = [
        "--study",
        paths.stem,
        "-b",
        str(paths.background),
        "-t",
        str(paths.training),
        "-o",
        str(paths.concerns),
        *_common_flags(args),
    ]
    return await mod._amain(argv)


async def _run_opening(args: argparse.Namespace, paths) -> int:
    from service.agent import opening_question as mod

    argv = [
        "--study",
        paths.stem,
        "-b",
        str(paths.background),
        "-c",
        str(paths.concerns),
        "-o",
        str(paths.opening),
        *_common_flags(args),
    ]
    if args.seed is not None:
        argv.extend(["--seed", str(args.seed)])
    return await mod._amain(argv)


async def _run_turn(args: argparse.Namespace, paths) -> int:
    from service.agent import patient_turn as mod

    argv = [
        "--study",
        paths.stem,
        "-b",
        str(paths.background),
        "-c",
        str(paths.concerns),
        "--opening",
        str(paths.opening),
        *_common_flags(args),
    ]
    if args.session:
        argv.extend(["--session", args.session])
    if args.crc is not None:
        argv.extend(["--crc", args.crc])
    if args.interactive:
        argv.append("--interactive")
    return await mod._amain(argv)


async def _run_evaluate(args: argparse.Namespace, paths) -> int:
    from service.agent import evaluation as mod

    if not args.session:
        print(
            "[FAIL] evaluate 需要 --session <dialogue_sessions/...>",
            file=sys.stderr,
        )
        return 1
    argv = [
        "--session",
        args.session,
        *_common_flags(args),
    ]
    if args.trainee:
        argv.extend(["--trainee", args.trainee])
    scenario = args.scenario or f"{paths.stem} 入组前知情沟通"
    argv.extend(["--scenario", scenario])
    return await mod._amain(argv)


async def _amain(argv: Iterable[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_studies:
        for stem in list_known_studies():
            print(stem)
        return 0

    try:
        stages = _expand_stages(args.stages)
    except ValueError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    paths = resolve_study(args.study)
    paths.ensure_parent_dirs()
    print(f"[pipeline] study={paths.stem} stages={stages}", file=sys.stderr)

    runners = {
        "background": _run_background,
        "concerns": _run_concerns,
        "opening": _run_opening,
        "turn": _run_turn,
        "evaluate": _run_evaluate,
    }

    for stage in stages:
        print(f"[pipeline] >>> {stage}", file=sys.stderr)
        code = await runners[stage](args, paths)
        if code != 0:
            print(f"[pipeline] stage {stage} failed exit={code}", file=sys.stderr)
            return code
    print("[pipeline] done", file=sys.stderr)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
