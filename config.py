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

# Google Maps API 配置
GOOGLE_MAPS_API_KEY: Final[str] = os.getenv("GOOGLE_MAPS_API_KEY", "")

# 設備資料庫配置
DEVICE_DB_PATH: Final[str] = os.getenv("DEVICE_DB_PATH", "data/devices.db")

# Server 時區配置
SERVER_TIMEZONE: Final[str] = os.getenv("SERVER_TIMEZONE", "Asia/Taipei")

# 確保 data 目錄存在
data_dir = os.path.dirname(DEVICE_DB_PATH)
if data_dir and not os.path.exists(data_dir):
    os.makedirs(data_dir, exist_ok=True)

