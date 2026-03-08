# refactor/core/session.py

from typing import Set, List, Dict, Any, Optional
from src.core.resource import ResourceRegistry, Resource
import discord

class SessionContext:
    """
    會話上下文實例。
    保存單次對話所需的所有狀態：資源註冊表、已載入技能、Discord 上下文等。
    """
    def __init__(self, guild: Optional[discord.Guild] = None, channel: Optional[discord.abc.Messageable] = None, loop: Any = None, discord_user_id: Optional[str] = None):
        # 資源管理
        self.loop = loop
        self.resources = ResourceRegistry()
        
        # 技能管理
        self.loaded_skill_names: Set[str] = set()
        self.active_tools: List[Any] = []  # 存儲實例化後的工具對象
        
        # Discord 上下文
        self.guild = guild
        self.channel = channel
        self.discord_user_id = discord_user_id  # Discord 用戶 ID
        
        # 額外元數據
        self.metadata: Dict[str, Any] = {}
        
        # 多模態控制開關 (預設為 True，允許注入多模態物件)
        self.enable_multimodal_injection = True

    def set_multimodal(self, enabled: bool):
        """設置多模態開關。"""
        self.enable_multimodal_injection = enabled

    def is_multimodal_enabled(self) -> bool:
        """檢查多模態是否啟用。"""
        return self.enable_multimodal_injection

    def add_image_resource(self, data: bytes, filename: str = "image.png") -> str:
        """快速添加圖片資源的輔助方法。"""
        res = Resource(data=data, mime_type="image/png", filename=filename)
        return self.resources.register(res)

    def add_audio_resource(self, data: bytes, filename: str = "voice.ogg", mime_type: str = "audio/ogg") -> str:
        """快速添加語音資源的輔助方法。"""
        res = Resource(data=data, mime_type=mime_type, filename=filename)
        return self.resources.register(res)

    def add_resource(self, data: bytes, filename: str, mime_type: str) -> str:
        """通用資源註冊輔助方法。"""
        res = Resource(data=data, mime_type=mime_type, filename=filename)
        return self.resources.register(res)

    def load_skill(self, skill_name: str):
        """標記技能為已載入。"""
        if skill_name not in self.loaded_skill_names:
            self.loaded_skill_names.add(skill_name)

    def is_skill_loaded(self, skill_name: str) -> bool:
        """檢查技能是否已載入。"""
        return skill_name in self.loaded_skill_names
