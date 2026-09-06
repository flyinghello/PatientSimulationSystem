"""联调测试：验证双向流式 TTS 模块能否正常合成。

用法（在项目根目录执行）：
  python tests/test_tts_generate.py
  python tests/test_tts_generate.py --emotions happy,sad
  python tests/test_tts_generate.py --stream
  python tests/test_tts_generate.py --text "今天有点不舒服" --out output/tts_test.mp3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# 保证从项目根目录可导入
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import setting  # noqa: E402  # 触发 load_dotenv
from service.agent.tts_emotion import DEFAULT_SPEAKER as EMO_SPEAKER  # noqa: E402
from service.agent.tts_generate import BidirectionalTTSAgent, TTSConfig  # noqa: E402


async def run_once(
    text: str,
    out: Path,
    *,
    stream_chars: bool = False,
    emotion: str | None = None,
    speaker: str | None = None,
) -> int:
    config = TTSConfig.from_env(
        emotion=emotion,
        speaker=speaker or (EMO_SPEAKER if emotion else None),
    )

    print("=== TTS 联调测试 ===")
    print(f"endpoint : {config.endpoint}")
    print(f"speaker  : {config.speaker}")
    print(f"resource : {config.resource_id}")
    print(f"emotion  : {config.emotion} (scale={config.emotion_scale})")
    print(f"api_key  : {'已配置' if setting.VOLC_API_KEY else '未配置'}")
    print(f"text     : {text}")
    print(f"out      : {out}")
    print()

    if not config.api_key and not (config.app_id and config.access_key):
        print("[FAIL] 未找到鉴权信息，请在 .env 填写 VOLC_API_KEY")
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)

    async def char_stream():
        for ch in text:
            yield ch
            await asyncio.sleep(0.02)

    source = char_stream() if stream_chars else text
    mode = "字符流式输入" if stream_chars else "整段输入"
    print(f"[1/3] 建连并开始合成（{mode}）...")

    t0 = time.perf_counter()
    bytes_written = 0
    first_chunk_ms: float | None = None

    try:
        async with BidirectionalTTSAgent(config) as agent:
            print("[2/3] 接收音频分片...")
            with out.open("wb") as f:
                async for chunk in agent.synthesize(source):
                    if first_chunk_ms is None:
                        first_chunk_ms = (time.perf_counter() - t0) * 1000
                        print(f"      首包延迟: {first_chunk_ms:.0f} ms")
                    f.write(chunk)
                    bytes_written += len(chunk)
    except Exception as exc:
        print(f"[FAIL] 合成失败: {type(exc).__name__}: {exc}")
        if out.exists() and out.stat().st_size == 0:
            out.unlink(missing_ok=True)
        return 2

    elapsed = (time.perf_counter() - t0) * 1000
    print("[3/3] 完成")
    print(f"      音频大小: {bytes_written} bytes")
    print(f"      总耗时  : {elapsed:.0f} ms")

    if bytes_written <= 0:
        print("[FAIL] 未收到任何音频数据")
        return 3

    print(f"[OK] 已写入 {out.resolve()}")
    return 0


async def run_emotions(text: str, emotions: list[str], stream_chars: bool) -> int:
    out_dir = ROOT / "output"
    codes = []
    for emo in emotions:
        out = out_dir / f"tts_{emo}.mp3"
        print("\n" + "=" * 60)
        code = await run_once(
            text,
            out,
            stream_chars=stream_chars,
            emotion=emo,
            speaker=EMO_SPEAKER,
        )
        codes.append(code)
    failed = [e for e, c in zip(emotions, codes) if c != 0]
    print("\n" + "=" * 60)
    if failed:
        print(f"[FAIL] 失败情绪: {', '.join(failed)}")
        return 2
    print("[OK] 全部情绪合成成功:")
    for emo in emotions:
        print(f"  - output/tts_{emo}.mp3")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="测试 TTS 双向流式模块")
    parser.add_argument(
        "--text",
        default="你好，我是模拟患者。今天感觉有些不舒服，胸口有点闷。",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "output" / "tts_test.mp3"),
    )
    parser.add_argument(
        "--emotion",
        default=None,
        help="单个情绪，如 happy / sad / angry",
    )
    parser.add_argument(
        "--emotions",
        default=None,
        help="多个情绪，逗号分隔，如 happy,sad",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="按字符流式送入文本，模拟 LLM 边生成边合成",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.emotions:
        emotions = [e.strip() for e in args.emotions.split(",") if e.strip()]
        code = asyncio.run(run_emotions(args.text, emotions, args.stream))
    else:
        code = asyncio.run(
            run_once(
                args.text,
                Path(args.out),
                stream_chars=args.stream,
                emotion=args.emotion,
            )
        )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
