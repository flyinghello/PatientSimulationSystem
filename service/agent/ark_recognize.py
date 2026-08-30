"""火山引擎豆包语音 — 大模型流式语音识别 (ASR) Agent。

文档：
https://docs.volcengine.com/docs/6561/1354869?lang=zh
（大模型流式语音识别 WebSocket；双向 / 优化双向 / 流式输入）

推荐流程：
  建连（Header 鉴权）
  → Full Client Request（JSON 配置，Gzip）
  → Audio Only Request × N（音频分片，末包负包）
  ⇄ Full Server Response（识别结果）
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import io
import json
import logging
import os
import struct
import uuid
import wave
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

# ===========================================================================
# 连接配置（密钥请写在项目根目录 .env，与 TTS 共用 VOLC_API_KEY）
# ===========================================================================
ASR_ENDPOINTS: dict[str, str] = {
    # 双向流式：每包输入对应返回，首字快
    "bigmodel": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel",
    # 双向流式优化版：仅结果变化时返包（官方推荐）
    "bigmodel_async": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async",
    # 流式输入：收尾包或 >15s 后出结果，准确率更高；支持 language
    "bigmodel_nostream": "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream",
}
DEFAULT_ENDPOINT_KEY = "bigmodel_async"
DEFAULT_ENDPOINT = ASR_ENDPOINTS[DEFAULT_ENDPOINT_KEY]
# 豆包流式语音识别 1.0 小时版；2.0 请改为 volc.seedasr.sauc.duration
DEFAULT_RESOURCE_ID = "volc.bigasr.sauc.duration"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_BITS = 16
DEFAULT_CHANNEL = 1
DEFAULT_SEGMENT_MS = 200  # 双向流式建议 200ms 分包
DEFAULT_LANGUAGE = "zh-CN"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------
class MsgType(IntEnum):
    FullClientRequest = 0b0001
    AudioOnlyClient = 0b0010
    FullServerResponse = 0b1001
    Error = 0b1111


class MsgFlag(IntEnum):
    NoSeq = 0b0000
    PositiveSeq = 0b0001
    LastNoSeq = 0b0010
    NegativeSeq = 0b0011


class Serialization(IntEnum):
    Raw = 0b0000
    JSON = 0b0001


class Compression(IntEnum):
    None_ = 0b0000
    Gzip = 0b0001


@dataclass
class AsrFrame:
    msg_type: MsgType = MsgType.FullClientRequest
    flag: MsgFlag = MsgFlag.PositiveSeq
    serialization: Serialization = Serialization.JSON
    compression: Compression = Compression.Gzip
    sequence: int = 0
    error_code: int = 0
    is_last: bool = False
    payload: bytes = b""

    def marshal(self) -> bytes:
        buf = io.BytesIO()
        buf.write(
            bytes(
                [
                    (0x1 << 4) | 0x1,
                    (int(self.msg_type) << 4) | int(self.flag),
                    (int(self.serialization) << 4) | int(self.compression),
                    0x00,
                ]
            )
        )
        if self.flag in (MsgFlag.PositiveSeq, MsgFlag.NegativeSeq):
            buf.write(struct.pack(">i", self.sequence))
        payload = self.payload
        if self.compression == Compression.Gzip and payload:
            payload = gzip.compress(payload)
        buf.write(struct.pack(">I", len(payload)))
        if payload:
            buf.write(payload)
        return buf.getvalue()

    @classmethod
    def unmarshal(cls, data: bytes) -> AsrFrame:
        if len(data) < 4:
            raise ValueError(f"frame too short: {len(data)}")

        header_size = (data[0] & 0x0F) * 4
        msg_type = MsgType(data[1] >> 4)
        flag_raw = data[1] & 0x0F
        serialization = Serialization(data[2] >> 4)
        compression = Compression(data[2] & 0x0F)

        offset = header_size
        sequence = 0
        is_last = bool(flag_raw & 0x02)
        if flag_raw & 0x01:
            sequence = struct.unpack_from(">i", data, offset)[0]
            offset += 4

        error_code = 0
        if msg_type == MsgType.Error:
            error_code = struct.unpack_from(">I", data, offset)[0]
            offset += 4

        payload = b""
        if offset + 4 <= len(data):
            payload_len = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            payload = data[offset : offset + payload_len]

        if compression == Compression.Gzip and payload:
            try:
                payload = gzip.decompress(payload)
            except OSError:
                logger.warning("gzip decompress failed, keep raw payload")

        try:
            flag = MsgFlag(flag_raw)
        except ValueError:
            flag = MsgFlag.NoSeq

        return cls(
            msg_type=msg_type,
            flag=flag,
            serialization=serialization,
            compression=compression,
            sequence=sequence,
            error_code=error_code,
            is_last=is_last,
            payload=payload,
        )

    def payload_json(self) -> dict[str, Any] | None:
        if not self.payload:
            return None
        try:
            return json.loads(self.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None


# ---------------------------------------------------------------------------
# Config / Result
# ---------------------------------------------------------------------------
@dataclass
class ASRConfig:
    app_id: str = ""
    access_key: str = ""
    api_key: str = ""
    resource_id: str = DEFAULT_RESOURCE_ID
    endpoint: str = DEFAULT_ENDPOINT
    uid: str = "patient-simulation"
    language: str = DEFAULT_LANGUAGE
    audio_format: str = "wav"
    codec: str = "raw"
    sample_rate: int = DEFAULT_SAMPLE_RATE
    bits: int = DEFAULT_BITS
    channel: int = DEFAULT_CHANNEL
    segment_ms: int = DEFAULT_SEGMENT_MS
    enable_itn: bool = True
    enable_punc: bool = True
    enable_ddc: bool = False
    show_utterances: bool = True
    result_type: str = "full"
    # 二遍识别仅 bigmodel_async 支持
    enable_nonstream: bool = False

    @classmethod
    def from_env(cls, **overrides: Any) -> ASRConfig:
        try:
            from config import setting as cfg
        except ImportError:  # pragma: no cover
            cfg = None

        def _get(name: str, *env_keys: str, default: str = "") -> str:
            for key in env_keys:
                val = os.getenv(key)
                if val:
                    return val.strip()
            if cfg is not None:
                val = getattr(cfg, name, "") or ""
                if val:
                    return str(val).strip()
            return default

        endpoint_key = (
            os.getenv("VOLC_ASR_ENDPOINT", DEFAULT_ENDPOINT_KEY).strip()
            or DEFAULT_ENDPOINT_KEY
        )
        if endpoint_key in ASR_ENDPOINTS:
            endpoint = ASR_ENDPOINTS[endpoint_key]
        elif endpoint_key.startswith(("ws://", "wss://")):
            endpoint = endpoint_key
        else:
            endpoint = DEFAULT_ENDPOINT

        values: dict[str, Any] = {
            "app_id": _get("VOLC_APP_ID", "VOLC_TTS_APP_ID", "VOLC_APP_ID"),
            "access_key": _get(
                "VOLC_ACCESS_KEY",
                "VOLC_TTS_ACCESS_KEY",
                "VOLC_ACCESS_TOKEN",
                "VOLC_ACCESS_KEY",
            ),
            "api_key": _get("VOLC_API_KEY", "VOLC_TTS_API_KEY", "VOLC_API_KEY"),
            "resource_id": _get(
                "VOLC_ASR_RESOURCE_ID",
                "VOLC_ASR_RESOURCE_ID",
                default=DEFAULT_RESOURCE_ID,
            ),
            "endpoint": endpoint,
            "language": os.getenv("VOLC_ASR_LANGUAGE", DEFAULT_LANGUAGE),
            "audio_format": os.getenv("VOLC_ASR_FORMAT", "wav"),
            "sample_rate": int(os.getenv("VOLC_ASR_SAMPLE_RATE", str(DEFAULT_SAMPLE_RATE))),
            "segment_ms": int(os.getenv("VOLC_ASR_SEGMENT_MS", str(DEFAULT_SEGMENT_MS))),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def build_headers(self) -> dict[str, str]:
        request_id = str(uuid.uuid4())
        headers = {
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Connect-Id": request_id,
            "X-Api-Sequence": "-1",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        elif self.app_id and self.access_key:
            headers["X-Api-App-Key"] = self.app_id
            headers["X-Api-Access-Key"] = self.access_key
        else:
            raise ValueError(
                "缺少鉴权信息：请在项目根目录 .env 中设置 VOLC_API_KEY，"
                "或 VOLC_APP_ID + VOLC_ACCESS_KEY"
            )
        return headers

    def full_client_payload(self) -> dict[str, Any]:
        audio: dict[str, Any] = {
            "format": self.audio_format,
            "codec": self.codec,
            "rate": self.sample_rate,
            "bits": self.bits,
            "channel": self.channel,
        }
        # language 仅流式输入模式正式支持；双向模式留空即可识别中文
        if self.language and "nostream" in self.endpoint:
            audio["language"] = self.language

        request: dict[str, Any] = {
            "model_name": "bigmodel",
            "enable_itn": self.enable_itn,
            "enable_punc": self.enable_punc,
            "enable_ddc": self.enable_ddc,
            "show_utterances": self.show_utterances,
            "result_type": self.result_type,
        }
        if self.enable_nonstream and "async" in self.endpoint:
            request["enable_nonstream"] = True

        return {
            "user": {"uid": self.uid},
            "audio": audio,
            "request": request,
        }


@dataclass
class ASRUtterance:
    text: str = ""
    start_time: int = 0
    end_time: int = 0
    definite: bool = False
    words: list[dict[str, Any]] = field(default_factory=list)
    additions: dict[str, Any] = field(default_factory=dict)


@dataclass
class ASRResult:
    text: str = ""
    utterances: list[ASRUtterance] = field(default_factory=list)
    duration_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)
    is_last: bool = False
    sequence: int = 0

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any] | None,
        *,
        is_last: bool = False,
        sequence: int = 0,
    ) -> ASRResult:
        if not payload:
            return cls(is_last=is_last, sequence=sequence)

        result_block = payload.get("result")
        text = ""
        utterances: list[ASRUtterance] = []

        if isinstance(result_block, dict):
            text = str(result_block.get("text") or "")
            raw_uts = result_block.get("utterances") or []
        elif isinstance(result_block, list) and result_block:
            first = result_block[0] if isinstance(result_block[0], dict) else {}
            text = str(first.get("text") or "")
            raw_uts = first.get("utterances") or result_block
        else:
            raw_uts = []

        if isinstance(raw_uts, list):
            for item in raw_uts:
                if not isinstance(item, dict):
                    continue
                utterances.append(
                    ASRUtterance(
                        text=str(item.get("text") or ""),
                        start_time=int(item.get("start_time") or 0),
                        end_time=int(item.get("end_time") or 0),
                        definite=bool(item.get("definite")),
                        words=list(item.get("words") or []),
                        additions=dict(item.get("additions") or {}),
                    )
                )

        audio_info = payload.get("audio_info") or {}
        duration = int(audio_info.get("duration") or 0) if isinstance(audio_info, dict) else 0
        return cls(
            text=text,
            utterances=utterances,
            duration_ms=duration,
            raw=payload,
            is_last=is_last,
            sequence=sequence,
        )


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def _guess_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"wav", "mp3", "ogg", "pcm"}:
        return suffix
    return "wav"


def _pcm_segment_size(sample_rate: int, bits: int, channel: int, segment_ms: int) -> int:
    bytes_per_sec = sample_rate * (bits // 8) * channel
    size = bytes_per_sec * segment_ms // 1000
    return max(size, 320)


def _read_wav_pcm(data: bytes) -> tuple[bytes, int, int, int]:
    with wave.open(io.BytesIO(data), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        pcm = wf.readframes(wf.getnframes())
    return pcm, sample_rate, sample_width * 8, channels


def iter_audio_chunks(data: bytes, segment_size: int) -> list[bytes]:
    if segment_size <= 0:
        return [data] if data else []
    return [data[i : i + segment_size] for i in range(0, len(data), segment_size)]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class StreamingASRAgent:
    """大模型流式 ASR：边发送音频边接收识别结果。"""

    def __init__(self, config: ASRConfig | None = None) -> None:
        self.config = config or ASRConfig.from_env()
        self._ws: ClientConnection | None = None
        self._seq = 1

    async def connect(self) -> None:
        if self._ws is not None:
            return
        try:
            self._ws = await websockets.connect(
                self.config.endpoint,
                additional_headers=self.config.build_headers(),
                max_size=10 * 1024 * 1024,
                ping_interval=20,
                open_timeout=30,
                proxy=None,
            )
        except Exception as exc:
            msg = str(exc)
            if "401" in msg or "403" in msg:
                raise RuntimeError(
                    "ASR 鉴权失败（HTTP 401/403）。"
                    "请确认 .env 中 VOLC_API_KEY 来自「豆包语音」控制台的 API Key，"
                    "并已开通「流式语音识别」服务。"
                ) from exc
            raise
        logger.info("ASR websocket connected: %s", self.config.endpoint)

    async def close(self) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.close()
        finally:
            self._ws = None

    async def __aenter__(self) -> StreamingASRAgent:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def start(self) -> ASRResult:
        """发送 Full Client Request，返回服务端首包响应。"""
        await self._ensure_connected()
        self._seq = 1
        payload = json.dumps(
            self.config.full_client_payload(),
            ensure_ascii=False,
        ).encode("utf-8")
        await self._send_frame(
            AsrFrame(
                msg_type=MsgType.FullClientRequest,
                flag=MsgFlag.PositiveSeq,
                serialization=Serialization.JSON,
                compression=Compression.Gzip,
                sequence=self._seq,
                payload=payload,
            )
        )
        self._seq += 1
        return await self._recv_result()

    async def send_audio(self, chunk: bytes, *, is_last: bool = False) -> None:
        if not chunk and not is_last:
            return
        await self._ensure_connected()
        seq = self._seq
        if is_last:
            flag = MsgFlag.NegativeSeq
            seq = -seq
        else:
            flag = MsgFlag.PositiveSeq
        await self._send_frame(
            AsrFrame(
                msg_type=MsgType.AudioOnlyClient,
                flag=flag,
                serialization=Serialization.Raw,
                compression=Compression.Gzip,
                sequence=seq,
                payload=chunk or b"",
            )
        )
        if not is_last:
            self._seq += 1

    async def iter_results(self) -> AsyncIterator[ASRResult]:
        """持续读取识别结果，直到末包或连接关闭。"""
        assert self._ws is not None
        while True:
            try:
                result = await self._recv_result()
            except websockets.ConnectionClosed:
                return
            yield result
            if result.is_last:
                return

    async def recognize_stream(
        self,
        chunks: Iterable[bytes] | AsyncIterator[bytes],
        *,
        pace: bool = False,
    ) -> AsyncIterator[ASRResult]:
        """双向流式识别：推送音频分片并 yield 中间/最终结果。"""
        await self.start()

        async def _pump() -> None:
            try:
                if hasattr(chunks, "__aiter__"):
                    async for chunk in chunks:  # type: ignore[union-attr]
                        if chunk:
                            await self.send_audio(chunk, is_last=False)
                            if pace:
                                await asyncio.sleep(self.config.segment_ms / 1000)
                else:
                    items = list(chunks)  # type: ignore[arg-type]
                    for i, chunk in enumerate(items):
                        is_last = i == len(items) - 1
                        await self.send_audio(chunk or b"", is_last=is_last)
                        if pace and not is_last:
                            await asyncio.sleep(self.config.segment_ms / 1000)
                    else:
                        if not items:
                            await self.send_audio(b"", is_last=True)
                        return
                await self.send_audio(b"", is_last=True)
            except Exception:
                logger.exception("ASR audio pump failed")
                raise

        pump = asyncio.create_task(_pump())
        try:
            async for result in self.iter_results():
                yield result
        finally:
            if not pump.done():
                pump.cancel()
                try:
                    await pump
                except asyncio.CancelledError:
                    pass
            else:
                await pump

    async def recognize_bytes(self, data: bytes, *, pace: bool = False) -> ASRResult:
        """识别整段音频字节，返回最终文本结果。"""
        fmt = self.config.audio_format.lower()
        audio = data
        if fmt == "wav":
            try:
                pcm, rate, bits, channels = _read_wav_pcm(data)
                self.config.audio_format = "pcm"
                self.config.codec = "raw"
                self.config.sample_rate = rate
                self.config.bits = bits
                self.config.channel = channels
                audio = pcm
                fmt = "pcm"
            except wave.Error:
                # 非标准 wav，按原始 wav 容器发送
                pass

        if fmt in {"pcm", "wav"}:
            segment_size = _pcm_segment_size(
                self.config.sample_rate,
                self.config.bits,
                self.config.channel,
                self.config.segment_ms,
            )
        else:
            # mp3/ogg：按约 128kbps 估算分包
            segment_size = max(int(16000 * self.config.segment_ms / 1000), 1024)

        parts = iter_audio_chunks(audio, segment_size)
        final = ASRResult()
        async for result in self.recognize_stream(parts, pace=pace):
            if result.text:
                final = result
            elif result.is_last and final.text:
                final.is_last = True
                final.duration_ms = result.duration_ms or final.duration_ms
                final.raw = result.raw or final.raw
        return final

    async def recognize_file(self, path: str | Path, *, pace: bool = False) -> ASRResult:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"音频文件不存在: {file_path}")
        data = file_path.read_bytes()
        if not self.config.audio_format or self.config.audio_format == "wav":
            self.config.audio_format = _guess_format(file_path)
        return await self.recognize_bytes(data, pace=pace)

    async def _ensure_connected(self) -> None:
        if self._ws is None:
            await self.connect()

    async def _send_frame(self, frame: AsrFrame) -> None:
        assert self._ws is not None
        await self._ws.send(frame.marshal())

    async def _recv_result(self) -> ASRResult:
        assert self._ws is not None
        raw = await self._ws.recv()
        if isinstance(raw, str):
            raise RuntimeError(f"unexpected text frame: {raw}")
        frame = AsrFrame.unmarshal(raw)
        if frame.msg_type == MsgType.Error:
            detail = frame.payload.decode("utf-8", errors="replace")
            raise RuntimeError(f"ASR error {frame.error_code}: {detail}")
        return ASRResult.from_payload(
            frame.payload_json(),
            is_last=frame.is_last,
            sequence=frame.sequence,
        )


async def recognize_file(
    path: str | Path,
    *,
    config: ASRConfig | None = None,
    pace: bool = False,
) -> ASRResult:
    """便捷函数：建连 → 识别文件 → 断开。"""
    async with StreamingASRAgent(config) as agent:
        return await agent.recognize_file(path, pace=pace)


async def recognize_bytes(
    data: bytes,
    *,
    config: ASRConfig | None = None,
    pace: bool = False,
) -> ASRResult:
    async with StreamingASRAgent(config) as agent:
        return await agent.recognize_bytes(data, pace=pace)


async def _main() -> None:
    parser = argparse.ArgumentParser(description="大模型流式 ASR 自测")
    parser.add_argument("--audio", required=True, help="音频文件路径（wav/mp3/pcm）")
    parser.add_argument(
        "--endpoint",
        default=None,
        choices=list(ASR_ENDPOINTS.keys()),
        help="接口别名：bigmodel / bigmodel_async / bigmodel_nostream",
    )
    parser.add_argument("--pace", action="store_true", help="按实时节奏发送音频分片")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    overrides: dict[str, Any] = {}
    if args.endpoint:
        overrides["endpoint"] = ASR_ENDPOINTS[args.endpoint]
    config = ASRConfig.from_env(**overrides)
    result = await recognize_file(args.audio, config=config, pace=args.pace)
    print(result.text)


if __name__ == "__main__":
    asyncio.run(_main())
