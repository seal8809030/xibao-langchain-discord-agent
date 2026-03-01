# refactor/core/resource.py

import uuid
import base64
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

@dataclass
class Resource:
    """
    通用資源封裝，支援圖片、影片、語音等 Bytes 數據。
    """
    data: bytes
    mime_type: str
    filename: str = "resource"
    id: str = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        # 清理 mime_type，移除如 ; charset=utf-8 等額外資訊，
        # 避免 LangChain Data URL 格式檢查失敗。
        if ";" in self.mime_type:
            self.mime_type = self.mime_type.split(";")[0].strip()

    def to_base64_url(self) -> str:
        """轉換為 Data URL 格式供模型使用。"""
        b64 = base64.b64encode(self.data).decode("utf-8")
        return f"data:{self.mime_type};base64,{b64}"

    def get_base64_data(self) -> str:
        """獲取純 base64 編碼數據（不含 data URL 前綴）。"""
        return base64.b64encode(self.data).decode("utf-8")

    def to_block(self) -> Any:
        """轉換為 LangChain 標準多模態內容區塊。"""
        if self.mime_type.startswith("image/"):
            # 使用 OpenAI 格式
            return {
                "type": "image_url",
                "image_url": {"url": self.to_base64_url()}
            }
        elif self.mime_type.startswith("audio/"):
            # 語音/音頻區塊 (使用 OpenAI 格式)
            if not self.data:
                return {
                    "type": "text",
                    "text": f"[無效的語音資源: {self.filename}]"
                }
            return {
                "type": "input_audio",
                "input_audio": {
                    "data": self.get_base64_data(),
                    "format": self._get_audio_format()
                }
            }
        
        # 預設回傳文字標記 (避免返回 None 導致 LangChain 報錯)
        return {
            "type": "text",
            "text": f"[資源: {self.filename} ({self.mime_type}) ID: {self.id}]"
        }

    def _get_audio_format(self) -> str:
        """根據 mime_type 獲取音頻格式。"""
        format_map = {
            "audio/ogg": "ogg",
            "audio/webm": "webm",
            "audio/mp3": "mp3",
            "audio/wav": "wav",
            "audio/mpeg": "mpeg",
            "audio/mp4": "mp4",
            "audio/x-m4a": "m4a",
        }
        return format_map.get(self.mime_type, "ogg")


class ResourceRegistry:
    """
    實例化的資源註冊表，每個會話擁有獨立的註冊表。
    """
    def __init__(self):
        self._storage: Dict[str, Resource] = {}
        self._focus_id: Optional[str] = None

    def register(self, resource: Resource) -> str:
        """註冊資源並回傳 ID。"""
        self._storage[resource.id] = resource
        return resource.id

    def get(self, resource_id: str) -> Optional[Resource]:
        """根據 ID 獲取資源。"""
        return self._storage.get(resource_id)

    def get_focused(self) -> Optional[Resource]:
        """獲取最近一次操作或註冊的資源。"""
        if self._focus_id:
            return self._storage.get(self._focus_id)
        return None

    def set_focus(self, resource_id: str):
        """設置當前焦點資源。"""
        if resource_id in self._storage:
            self._focus_id = resource_id

    def list_all(self) -> List[Resource]:
        """列出所有註冊的資源。"""
        return list(self._storage.values())

    def unregister(self, resource_id: str):
        """註銷資源。"""
        if resource_id in self._storage:
            del self._storage[resource_id]
            if self._focus_id == resource_id:
                self._focus_id = None

    def clear_focus(self):
        """清除當前焦點。"""
        self._focus_id = None
