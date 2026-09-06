"""从项目根目录 .env 加载配置。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env", override=False)


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# 新版控制台：只需 API Key（语音 ASR / TTS）
VOLC_API_KEY = env("VOLC_API_KEY") or env("VOLC_TTS_API_KEY")

# 旧版控制台备用（一般不用填）
VOLC_APP_ID = env("VOLC_APP_ID") or env("VOLC_TTS_APP_ID")
VOLC_ACCESS_KEY = (
    env("VOLC_ACCESS_KEY")
    or env("VOLC_ACCESS_TOKEN")
    or env("VOLC_TTS_ACCESS_KEY")
)

# 火山方舟文本生成（情景扮演 / 问题生成，doubao-seed-character）
# 模型可填模型名（如 doubao-seed-character-251128）或推理接入点 ID（ep-xxx）
ARK_API_KEY = (
    env("TEXT_GENERATION_API_KEY")
    or env("ARK_API_KEY")
    or env("VOLC_ARK_API_KEY")
)
ARK_MODEL = (
    env("TEXT_GENERATION_MODEL")
    or env("ARK_MODEL")
    or "doubao-seed-character-251128"
)
ARK_BASE_URL = (
    env("ARK_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3"
)
