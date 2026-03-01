# refactor/skills/discordEventsTools/tools.py

import datetime
import discord
import asyncio
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from MyLogger import ShowLog, ShowErrorLog
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from src.core.session import SessionContext

def get_tools(context: "SessionContext") -> List[Any]:
    """
    獲取與會話實例綁定的 Discord 活動管理工具。
    """
    
    def _run_async(coro):
        """輔助函數：在會話綁定的事件迴圈中執行協程。"""
        loop = context.loop
        try:
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        except Exception as e:
            # 備援：如果 loop 發生錯誤
            ShowErrorLog(f"[Async輔助] 執行錯誤: {e}")
            raise e

    def _parse_iso_time(iso_str: str) -> datetime.datetime:
        dt = datetime.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            # 預設台北時區
            tz = datetime.timezone(datetime.timedelta(hours=8))
            dt = dt.replace(tzinfo=tz)
        return dt

    @tool
    def create_discord_event(
        name: str, 
        description: str, 
        start_time_iso: str, 
        location: str, 
        end_time_iso: Optional[str] = None
    ) -> Dict[str, Any]:
        """建立 Discord 伺服器活動。"""
        try:
            guild = context.guild
            if not guild: return {"err": "目前會話未關聯 Discord 伺服器。"}

            start_time = _parse_iso_time(start_time_iso)
            end_time = _parse_iso_time(end_time_iso) if end_time_iso else start_time + datetime.timedelta(hours=1)

            create_kwargs = {
                "name": name,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "entity_type": discord.EntityType.external,
                "location": location,
                "privacy_level": discord.PrivacyLevel.guild_only
            }
            
            event = _run_async(guild.create_scheduled_event(**create_kwargs))
            return {"id": str(event.id), "name": event.name, "url": event.url, "msg": "活動建立成功。"}
        except Exception as e:
            ShowErrorLog(f"create_discord_event failed: {e}")
            return {"err": str(e)}

    @tool
    def update_discord_event(
        event_id: str, 
        name: Optional[str] = None, 
        description: Optional[str] = None, 
        start_time_iso: Optional[str] = None, 
        end_time_iso: Optional[str] = None, 
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """修改現有活動資訊。"""
        try:
            guild = context.guild
            if not guild: return {"err": "目前會話未關聯 Discord 伺服器。"}

            event = _run_async(guild.fetch_scheduled_event(int(event_id)))
            
            update_kwargs = {}
            if name: update_kwargs["name"] = name
            if description: update_kwargs["description"] = description
            if start_time_iso: update_kwargs["start_time"] = _parse_iso_time(start_time_iso)
            if end_time_iso: update_kwargs["end_time"] = _parse_iso_time(end_time_iso)
            if location: update_kwargs["location"] = location

            if not update_kwargs: return {"err": "沒有提供變更欄位。"}

            updated_event = _run_async(event.edit(**update_kwargs))
            return {"id": str(updated_event.id), "status": "updated", "msg": "更新成功。"}
        except discord.NotFound:
            return {"err": "找不到該活動。"}
        except Exception as e:
            ShowErrorLog(f"update_discord_event failed: {e}")
            return {"err": str(e)}

    @tool
    def list_discord_events() -> Dict[str, Any]:
        """列出伺服器中所有活動。"""
        try:
            guild = context.guild
            if not guild: return {"err": "目前會話未關聯 Discord 伺服器。"}

            events = guild.scheduled_events or _run_async(guild.fetch_scheduled_events())
            
            event_list = [{
                "id": str(e.id),
                "name": e.name,
                "start_time": e.start_time.isoformat(),
                "location": e.location,
                "status": str(e.status)
            } for e in events]
            
            return {"events": event_list, "msg": f"共找到 {len(event_list)} 個活動"}
        except Exception as e:
            return {"err": str(e)}

    @tool
    def delete_discord_event(event_id: str) -> Dict[str, Any]:
        """刪除指定的活動。"""
        try:
            guild = context.guild
            if not guild: return {"err": "目前會話未關聯 Discord 伺服器。"}

            event = _run_async(guild.fetch_scheduled_event(int(event_id)))
            _run_async(event.delete())
            return {"msg": "活動已刪除。"}
        except discord.NotFound:
            return {"err": "找不到該活動。"}
        except Exception as e:
            return {"err": str(e)}

    @tool
    def list_event_users(event_id: str) -> Dict[str, Any]:
        """列出感興趣的成員。"""
        try:
            guild = context.guild
            if not guild: return {"err": "目前會話未關聯 Discord 伺服器。"}

            event = _run_async(guild.fetch_scheduled_event(int(event_id)))
            
            async def fetch_users():
                users = []
                async for user in event.users():
                    users.append({"name": user.display_name, "id": str(user.id)})
                return users
                
            users = _run_async(fetch_users())
            return {"users": users, "msg": f"共找到 {len(users)} 位成員"}
        except Exception as e:
            return {"err": str(e)}

    return [
        create_discord_event, 
        update_discord_event, 
        list_discord_events, 
        delete_discord_event, 
        list_event_users
    ]
