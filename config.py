# config.py

import os
import sys
from typing import Final, Optional
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

def get_env_or_raise(key: str, default: Optional[str] = None) -> str:
    """獲取環境變量，若不存在則拋出錯誤 (除非提供預設值)。"""
    value = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value

# Discord 配置
DISCORD_BOT_TOKEN: Final[str] = get_env_or_raise("DISCORD_BOT_TOKEN")

# AI 代理配置
AI_API_KEY: Final[str] = get_env_or_raise("AI_API_KEY")
AI_API_BASE: Final[str] = get_env_or_raise("AI_API_BASE", "http://localhost:10909")
AI_MODEL_ID: Final[str] = get_env_or_raise("AI_MODEL_ID", "gemini-3-flash")

# 啟動偵錯日誌：確認環境變量載入情況
if os.getenv("PYTHONUNBUFFERED") == "1":
    print(f"[DEBUG] 偵測到 Docker 環境", file=sys.stderr)
    print(f"[DEBUG] AI_API_BASE: {AI_API_BASE}", file=sys.stderr)
    print(f"[DEBUG] AI_MODEL_ID: {AI_MODEL_ID}", file=sys.stderr)
