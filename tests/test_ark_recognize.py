"""联调测试：验证大模型流式 ASR 模块能否识别中文语音。

用法（在项目根目录执行）：
  python tests/test_ark_recognize.py
  python tests/test_ark_recognize.py --audio output/tts_test.mp3
  python tests/test_ark_recognize.py --text "今天有点不舒服" --endpoint bigmodel_nostream
  python tests/test_ark_recognize.py --pace
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import time
from pathlib import Path

# 保证从项目根目录可导入
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import setting  # noqa: E402  # 触发 load_dotenv
from service.agent.ark_recognize import (  # noqa: E402
    ASR_ENDPOINTS,
    ASRConfig,
    StreamingASRAgent,
)
from service.agent.tts_generate import BidirectionalTTSAgent, TTSConfig  # noqa: E402

DEFAULT_ZH_TEXT = "你好，我是模拟患者。今天感觉有些不舒服，胸口有点闷。"


def _normalize(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


async def synthesize_zh_audio(text: str, out: Path) -> Path:
    """用现有 TTS 合成中文语音，供 ASR 识别。"""
    config = TTSConfig.from_env(emotion=None)
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"[TTS] 合成中文语音 → {out}")
    async with BidirectionalTTSAgent(config) as agent:
        await agent.synthesize_to_file(text, str(out))
    size = out.stat().st_size if out.exists() else 0
    print(f"[TTS] 完成，大小 {size} bytes")
    if size <= 0:
        raise RuntimeError("TTS 未生成有效音频")
    return out


async def run_once(
    audio: Path,
    *,
    expect_text: str,
    endpoint: str | None = None,
    pace: bool = False,
) -> int:
    overrides: dict = {
        "audio_format": audio.suffix.lower().lstrip(".") or "mp3",
    }
    if endpoint:
        overrides["endpoint"] = ASR_ENDPOINTS.get(endpoint, endpoint)

    config = ASRConfig.from_env(**overrides)

    print("=== ASR 联调测试 ===")
    print(f"endpoint : {config.endpoint}")
    print(f"resource : {config.resource_id}")
    print(f"language : {config.language}")
    print(f"format   : {config.audio_format}")
    print(f"api_key  : {'已配置' if setting.VOLC_API_KEY else '未配置'}")
    print(f"audio    : {audio}")
    print(f"expect   : {expect_text}")
    print()

    if not config.api_key and not (config.app_id and config.access_key):
        print("[FAIL] 未找到鉴权信息，请在 .env 填写 VOLC_API_KEY")
        return 1

    if not audio.is_file():
        print(f"[FAIL] 音频文件不存在: {audio}")
        return 1

    print("[1/3] 建连并开始识别...")
    t0 = time.perf_counter()
    partials: list[str] = []
    final_text = ""

    try:
        async with StreamingASRAgent(config) as agent:
            print("[2/3] 推送音频并接收结果...")
            result = await agent.recognize_file(audio, pace=pace)
            final_text = result.text or ""
            for utt in result.utterances:
                if utt.text:
                    partials.append(utt.text)
            elapsed = (time.perf_counter() - t0) * 1000
            print("[3/3] 完成")
            print(f"      识别文本: {final_text}")
            print(f"      分句数  : {len(result.utterances)}")
            print(f"      时长    : {result.duration_ms} ms")
            print(f"      总耗时  : {elapsed:.0f} ms")
    except Exception as exc:
        print(f"[FAIL] 识别失败: {type(exc).__name__}: {exc}")
        return 2

    if not final_text.strip():
        print("[FAIL] 未识别到任何文本")
        return 3

    # 中文关键词抽检：去掉标点后，期望句子里至少一半有效字出现在结果中
    expect_norm = _normalize(expect_text)
    got_norm = _normalize(final_text)
    # 取期望文本中长度≥2的连续片段做宽松匹配
    keywords = [expect_norm[i : i + 2] for i in range(0, max(len(expect_norm) - 1, 0), 2)]
    keywords = [k for k in keywords if k]
    hit = sum(1 for k in keywords if k in got_norm) if keywords else 0
    ratio = (hit / len(keywords)) if keywords else 0.0

    print(f"      关键词命中: {hit}/{len(keywords)} ({ratio:.0%})")
    if ratio < 0.4:
        print("[FAIL] 识别结果与期望中文文本相差过大")
        print(f"       expect≈ {expect_text}")
        print(f"       got   ≈ {final_text}")
        return 4

    print(f"[OK] 中文识别成功: {final_text}")
    return 0


async def prepare_and_run(
    *,
    text: str,
    audio: Path | None,
    endpoint: str | None,
    pace: bool,
    skip_tts: bool,
) -> int:
    expect = text
    if audio is not None:
        path = audio
    else:
        out = ROOT / "output" / "asr_zh_test.mp3"
        if skip_tts and out.is_file() and out.stat().st_size > 0:
            path = out
            print(f"[INFO] 复用已有音频: {path}")
        else:
            try:
                path = await synthesize_zh_audio(text, out)
            except Exception as exc:
                print(f"[FAIL] TTS 合成中文语音失败: {type(exc).__name__}: {exc}")
                return 5

    return await run_once(path, expect_text=expect, endpoint=endpoint, pace=pace)


def main() -> None:
    parser = argparse.ArgumentParser(description="测试大模型流式 ASR（中文语音）")
    parser.add_argument(
        "--text",
        default=DEFAULT_ZH_TEXT,
        help="用于 TTS 合成的中文文本（未指定 --audio 时）",
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="已有音频路径；不传则先用 TTS 合成中文再识别",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        choices=list(ASR_ENDPOINTS.keys()),
        help="ASR 接口：bigmodel / bigmodel_async / bigmodel_nostream",
    )
    parser.add_argument(
        "--pace",
        action="store_true",
        help="按实时节奏发送音频分片",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="若 output/asr_zh_test.mp3 已存在则直接复用",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    audio = Path(args.audio) if args.audio else None
    code = asyncio.run(
        prepare_and_run(
            text=args.text,
            audio=audio,
            endpoint=args.endpoint,
            pace=args.pace,
            skip_tts=args.skip_tts,
        )
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
