"""火山引擎豆包语音 — WebSocket 双向流式 TTS Agent。

文档：
https://docs.volcengine.com/docs/6561/1329505
（双向流式语音合成 WebSocket V3；与 6561/2532486 为同系列接口）

推荐流程：
  StartConnection → ConnectionStarted
  StartSession    → SessionStarted
  TaskRequest(文本流) ⇄ TTSResponse(音频流)
  FinishSession   → SessionFinished
  FinishConnection → ConnectionFinished
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import os
import struct
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

# ===========================================================================
# 连接与语气配置（语气改这里；密钥请写在项目根目录 .env）
# ===========================================================================
TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
DEFAULT_SPEAKER = "zh_female_gaolengyujie_emo_v2_mars_bigtts"  # 高冷御姐（多情感，含 fear/hate）
DEFAULT_RESOURCE_ID = "seed-tts-1.0"  # 2.0 音色请改为 seed-tts-2.0

# 语气 / 情感：部分音色支持，如 happy / sad / angry / surprised / fear /
# hate / excited / coldness / neutral 等；不需要时设为 None
DEFAULT_EMOTION: str | None = "neutral"  # 须为当前音色支持的官方枚举
# 情绪强度 1~5，越大越明显；仅在设置了 DEFAULT_EMOTION 时生效
DEFAULT_EMOTION_SCALE: int = 4
# 语速 [-50, 100]：0 原速，100≈2 倍，-50≈0.5 倍
DEFAULT_SPEECH_RATE: int = 0
# 音量 [-50, 100]：0 原音量
DEFAULT_LOUDNESS_RATE: int = 0
# TTS2.0 语音指令（仅 seed-tts-2.0 / ICL2.0 表现力增强版有效），例如：
# ["你可以用虚弱、略带痛苦的语气说话吗？"]；不需要时设为 None
DEFAULT_CONTEXT_TEXTS: list[str] | None = None
# ===========================================================================


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------
class MsgType(IntEnum):
    FullClientRequest = 0b0001
    AudioOnlyClient = 0b0010
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    Error = 0b1111


class MsgFlag(IntEnum):
    NoSeq = 0b0000
    PositiveSeq = 0b0001
    LastNoSeq = 0b0010
    NegativeSeq = 0b0011
    WithEvent = 0b0100


class Serialization(IntEnum):
    Raw = 0b0000
    JSON = 0b0001


class Compression(IntEnum):
    None_ = 0b0000
    Gzip = 0b0001


class Event(IntEnum):
    StartConnection = 1
    FinishConnection = 2
    ConnectionStarted = 50
    ConnectionFailed = 51
    ConnectionFinished = 52
    StartSession = 100
    CancelSession = 101
    FinishSession = 102
    SessionStarted = 150
    SessionCanceled = 151
    SessionFinished = 152
    SessionFailed = 153
    TaskRequest = 200
    TTSSentenceStart = 350
    TTSSentenceEnd = 351
    TTSResponse = 352


_CONNECTION_EVENTS = frozenset(
    {
        Event.StartConnection,
        Event.FinishConnection,
        Event.ConnectionStarted,
        Event.ConnectionFailed,
        Event.ConnectionFinished,
    }
)


@dataclass
class Frame:
    msg_type: MsgType = MsgType.FullClientRequest
    flag: MsgFlag = MsgFlag.WithEvent
    serialization: Serialization = Serialization.JSON
    compression: Compression = Compression.None_
    event: Event = Event.StartConnection
    session_id: str = ""
    connect_id: str = ""
    error_code: int = 0
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
        if self.flag == MsgFlag.WithEvent:
            buf.write(struct.pack(">i", int(self.event)))
            if self.event not in _CONNECTION_EVENTS:
                sid = self.session_id.encode("utf-8")
                buf.write(struct.pack(">I", len(sid)))
                if sid:
                    buf.write(sid)
        if self.msg_type == MsgType.Error:
            buf.write(struct.pack(">I", self.error_code & 0xFFFFFFFF))
        buf.write(struct.pack(">I", len(self.payload)))
        if self.payload:
            buf.write(self.payload)
        return buf.getvalue()

    @classmethod
    def unmarshal(cls, data: bytes) -> Frame:
        if len(data) < 4:
            raise ValueError(f"frame too short: {len(data)}")

        header_size = (data[0] & 0x0F) * 4
        frame = cls(
            msg_type=MsgType(data[1] >> 4),
            flag=MsgFlag(data[1] & 0x0F),
            serialization=Serialization(data[2] >> 4),
            compression=Compression(data[2] & 0x0F),
        )
        offset = header_size

        if frame.flag == MsgFlag.WithEvent:
            frame.event = Event(struct.unpack_from(">i", data, offset)[0])
            offset += 4
            if frame.event not in _CONNECTION_EVENTS:
                sid_len = struct.unpack_from(">I", data, offset)[0]
                offset += 4
                if sid_len:
                    frame.session_id = data[offset : offset + sid_len].decode("utf-8")
                    offset += sid_len
            elif frame.msg_type == MsgType.FullServerResponse and offset + 4 <= len(data):
                peek_len = struct.unpack_from(">I", data, offset)[0]
                if offset + 4 + peek_len + 4 <= len(data):
                    offset += 4
                    frame.connect_id = data[offset : offset + peek_len].decode(
                        "utf-8", errors="replace"
                    )
                    offset += peek_len

        if frame.msg_type == MsgType.Error:
            frame.error_code = struct.unpack_from(">I", data, offset)[0]
            offset += 4

        if offset + 4 <= len(data):
            payload_len = struct.unpack_from(">I", data, offset)[0]
            offset += 4
            frame.payload = data[offset : offset + payload_len]
        return frame

    def payload_json(self) -> dict[str, Any] | None:
        if not self.payload:
            return None
        try:
            return json.loads(self.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class TTSConfig:
    app_id: str = ""
    access_key: str = ""
    api_key: str = ""
    resource_id: str = DEFAULT_RESOURCE_ID
    speaker: str = DEFAULT_SPEAKER
    audio_format: str = "mp3"
    sample_rate: int = 24000
    speech_rate: int = DEFAULT_SPEECH_RATE
    loudness_rate: int = DEFAULT_LOUDNESS_RATE
    emotion: str | None = DEFAULT_EMOTION
    emotion_scale: int = DEFAULT_EMOTION_SCALE
    context_texts: list[str] | None = None
    uid: str = "patient-simulation"
    endpoint: str = TTS_ENDPOINT

    def __post_init__(self) -> None:
        if self.context_texts is None and DEFAULT_CONTEXT_TEXTS is not None:
            self.context_texts = list(DEFAULT_CONTEXT_TEXTS)

    @classmethod
    def from_env(cls, **overrides: Any) -> TTSConfig:
        # 读取 .env（config.setting 已 load_dotenv）
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
                "VOLC_TTS_RESOURCE_ID",
                "VOLC_TTS_RESOURCE_ID",
                default=DEFAULT_RESOURCE_ID,
            ),
            "speaker": _get(
                "VOLC_TTS_SPEAKER",
                "VOLC_TTS_SPEAKER",
                default=DEFAULT_SPEAKER,
            ),
            "audio_format": os.getenv("VOLC_TTS_FORMAT", "mp3"),
            "sample_rate": int(os.getenv("VOLC_TTS_SAMPLE_RATE", "24000")),
            "emotion": os.getenv("VOLC_TTS_EMOTION", DEFAULT_EMOTION),
            "emotion_scale": int(
                os.getenv("VOLC_TTS_EMOTION_SCALE", str(DEFAULT_EMOTION_SCALE))
            ),
            "speech_rate": int(
                os.getenv("VOLC_TTS_SPEECH_RATE", str(DEFAULT_SPEECH_RATE))
            ),
            "loudness_rate": int(
                os.getenv("VOLC_TTS_LOUDNESS_RATE", str(DEFAULT_LOUDNESS_RATE))
            ),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    def build_headers(self) -> dict[str, str]:
        headers = {
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        elif self.app_id and self.access_key:
            headers["X-Api-App-Id"] = self.app_id
            headers["X-Api-Access-Key"] = self.access_key
        else:
            raise ValueError(
                "缺少鉴权信息：请在项目根目录 .env 中设置 VOLC_API_KEY，"
                "或 VOLC_APP_ID + VOLC_ACCESS_KEY"
            )
        return headers

    def session_payload(
        self,
        *,
        event: Event | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        audio_params: dict[str, Any] = {
            "format": self.audio_format,
            "sample_rate": self.sample_rate,
            "speech_rate": self.speech_rate,
            "loudness_rate": self.loudness_rate,
        }
        if self.emotion:
            # emotion 必须是当前音色支持的官方枚举；非法值会导致合成失败或被忽略
            from service.agent.tts_emotion import clamp_emotion

            audio_params["emotion"] = clamp_emotion(
                self.emotion, speaker=self.speaker
            )
            audio_params["emotion_scale"] = max(1, min(5, int(self.emotion_scale)))

        req_params: dict[str, Any] = {
            "speaker": self.speaker,
            "audio_params": audio_params,
        }
        if text is not None:
            req_params["text"] = text
        if self.context_texts:
            req_params["additions"] = {
                "context_texts": self.context_texts,
            }

        body: dict[str, Any] = {
            "user": {"uid": self.uid},
            "namespace": "BidirectionalTTS",
            "req_params": req_params,
        }
        if event is not None:
            body["event"] = int(event)
        return body


@dataclass
class TTSChunk:
    event: Event
    audio: bytes = b""
    meta: dict[str, Any] = field(default_factory=dict)
    session_id: str = ""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class BidirectionalTTSAgent:
    """双向流式 TTS：边发送文本边接收音频。"""

    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig.from_env()
        self._ws: ClientConnection | None = None
        self._session_id = ""
        self._connected = False
        self._session_active = False

    async def connect(self) -> None:
        if self._connected:
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
                    "TTS 鉴权失败（HTTP 401/403）。"
                    "请确认 .env 中 VOLC_API_KEY 来自「豆包语音」控制台的 API Key，"
                    "不是方舟 Ark（ark- 开头）的大模型 Key。"
                ) from exc
            raise

        await self._send_event(Event.StartConnection, payload=b"{}")
        frame = await self._recv()
        if frame.event != Event.ConnectionStarted:
            raise RuntimeError(
                f"建连失败: event={frame.event.name}, payload={frame.payload!r}"
            )
        self._connected = True
        logger.info("TTS connection started, connect_id=%s", frame.connect_id or "-")

    async def close(self) -> None:
        if not self._ws:
            return
        try:
            if self._session_active:
                await self.cancel_session()
            if self._connected:
                await self._send_event(Event.FinishConnection, payload=b"{}")
                try:
                    await asyncio.wait_for(self._recv(), timeout=5)
                except Exception:
                    pass
        finally:
            await self._ws.close()
            self._ws = None
            self._connected = False
            self._session_active = False

    async def __aenter__(self) -> BidirectionalTTSAgent:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def start_session(self, session_id: str | None = None) -> str:
        await self._ensure_connected()
        if self._session_active:
            raise RuntimeError("当前连接已有活跃 session，请先 finish_session")

        self._session_id = session_id or str(uuid.uuid4())
        payload = json.dumps(
            self.config.session_payload(event=Event.StartSession),
            ensure_ascii=False,
        ).encode("utf-8")
        await self._send_event(
            Event.StartSession,
            session_id=self._session_id,
            payload=payload,
        )
        frame = await self._recv()
        if frame.event != Event.SessionStarted:
            raise RuntimeError(
                f"StartSession 失败: event={frame.event.name}, payload={frame.payload!r}"
            )
        self._session_active = True
        logger.info("TTS session started: %s", self._session_id)
        return self._session_id

    async def send_text(self, text: str) -> None:
        """向当前 session 推送文本（可多次调用，适配 LLM 流式输出）。"""
        if not self._session_active:
            raise RuntimeError("session 未启动，请先 start_session()")
        if not text:
            return
        payload = json.dumps(
            self.config.session_payload(event=Event.TaskRequest, text=text),
            ensure_ascii=False,
        ).encode("utf-8")
        await self._send_event(
            Event.TaskRequest,
            session_id=self._session_id,
            payload=payload,
        )

    async def finish_session(self) -> None:
        if not self._session_active:
            return
        await self._send_event(
            Event.FinishSession,
            session_id=self._session_id,
            payload=b"{}",
        )

    async def cancel_session(self) -> None:
        if not self._session_active:
            return
        await self._send_event(
            Event.CancelSession,
            session_id=self._session_id,
            payload=b"{}",
        )
        self._session_active = False

    async def iter_response(self) -> AsyncIterator[TTSChunk]:
        """消费下行事件，直到 SessionFinished。"""
        while True:
            frame = await self._recv()

            if frame.msg_type == MsgType.Error:
                detail = frame.payload.decode("utf-8", errors="replace")
                raise RuntimeError(f"TTS error {frame.error_code}: {detail}")

            if frame.event == Event.TTSResponse or (
                frame.msg_type == MsgType.AudioOnlyServer and frame.payload
            ):
                yield TTSChunk(
                    event=Event.TTSResponse,
                    audio=frame.payload,
                    session_id=frame.session_id or self._session_id,
                )
                continue

            if frame.event in (Event.TTSSentenceStart, Event.TTSSentenceEnd):
                yield TTSChunk(
                    event=frame.event,
                    meta=frame.payload_json() or {},
                    session_id=frame.session_id or self._session_id,
                )
                continue

            if frame.event == Event.SessionFinished:
                self._session_active = False
                yield TTSChunk(
                    event=frame.event,
                    meta=frame.payload_json() or {},
                    session_id=frame.session_id or self._session_id,
                )
                return

            if frame.event in (Event.SessionCanceled, Event.SessionFailed):
                self._session_active = False
                raise RuntimeError(
                    f"{frame.event.name}: "
                    f"{frame.payload.decode('utf-8', errors='replace')}"
                )

            logger.debug("ignore event=%s", frame.event)

    async def synthesize(
        self,
        text: str | Iterable[str] | AsyncIterator[str],
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[bytes]:
        """双向流式合成：文本可整段或分片输入，yield 音频分片。"""
        await self.start_session(session_id=session_id)

        async def _pump_text() -> None:
            try:
                if isinstance(text, str):
                    await self.send_text(text)
                elif hasattr(text, "__aiter__"):
                    async for chunk in text:  # type: ignore[union-attr]
                        if chunk:
                            await self.send_text(str(chunk))
                else:
                    for chunk in text:  # type: ignore[union-attr]
                        if chunk:
                            await self.send_text(str(chunk))
            finally:
                await self.finish_session()

        pump = asyncio.create_task(_pump_text())
        try:
            async for item in self.iter_response():
                if item.audio:
                    yield item.audio
        finally:
            if not pump.done():
                pump.cancel()
                try:
                    await pump
                except asyncio.CancelledError:
                    pass
            else:
                await pump

    async def synthesize_to_bytes(
        self,
        text: str | Iterable[str] | AsyncIterator[str],
        **kwargs: Any,
    ) -> bytes:
        buf = bytearray()
        async for chunk in self.synthesize(text, **kwargs):
            buf.extend(chunk)
        return bytes(buf)

    async def synthesize_to_file(
        self,
        text: str | Iterable[str] | AsyncIterator[str],
        output_path: str,
        **kwargs: Any,
    ) -> str:
        data = await self.synthesize_to_bytes(text, **kwargs)
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path

    async def _ensure_connected(self) -> None:
        if not self._connected or not self._ws:
            await self.connect()

    async def _send_event(
        self,
        event: Event,
        *,
        session_id: str = "",
        payload: bytes = b"{}",
    ) -> None:
        assert self._ws is not None
        frame = Frame(
            msg_type=MsgType.FullClientRequest,
            flag=MsgFlag.WithEvent,
            serialization=Serialization.JSON,
            event=event,
            session_id=session_id,
            payload=payload,
        )
        await self._ws.send(frame.marshal())

    async def _recv(self) -> Frame:
        assert self._ws is not None
        raw = await self._ws.recv()
        if isinstance(raw, str):
            raise RuntimeError(f"unexpected text frame: {raw}")
        return Frame.unmarshal(raw)


async def stream_tts(
    text: str | Iterable[str] | AsyncIterator[str],
    *,
    config: TTSConfig | None = None,
) -> AsyncIterator[bytes]:
    """便捷函数：建连 → 双向流式合成 → 断开。"""
    async with BidirectionalTTSAgent(config) as agent:
        async for chunk in agent.synthesize(text):
            yield chunk


async def _main() -> None:
    parser = argparse.ArgumentParser(description="双向流式 TTS 自测")
    parser.add_argument("--text", default="你好，我是模拟患者，今天感觉有些不舒服。")
    parser.add_argument("--out", default="tts_output.mp3")
    parser.add_argument("--speaker", default=None)
    parser.add_argument("--resource-id", default=None)
    parser.add_argument("--stream-chars", action="store_true", help="按字符流式送入文本")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    config = TTSConfig.from_env(
        speaker=args.speaker,
        resource_id=args.resource_id,
    )

    async def char_stream() -> AsyncIterator[str]:
        for ch in args.text:
            yield ch
            await asyncio.sleep(0.02)

    source: str | AsyncIterator[str] = char_stream() if args.stream_chars else args.text

    async with BidirectionalTTSAgent(config) as agent:
        path = await agent.synthesize_to_file(source, args.out)
        print(f"saved: {path}")


if __name__ == "__main__":
    asyncio.run(_main())
