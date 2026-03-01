# refactor/skills/infra.py

import os
import re
import json
import yaml
import datetime
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from MyLogger import ShowLog, ShowErrorLog
from src.core.session import SessionContext

class SkillParser:
    @staticmethod
    def parse(skill_name: str) -> Dict[str, Any]:
        file_path = f"src/skills/{skill_name}/SKILL.md"
        if not os.path.exists(file_path):
            return {"err": f"Skill definition not found: {file_path}"}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                return {"metadata": {}, "body": content, "msg": "No frontmatter found"}
            
            yaml_text, body = match.group(1), match.group(2)
            metadata = yaml.safe_load(yaml_text) or {}
            
            return {"metadata": metadata, "body": body, "msg": "Success"}
        except Exception as e:
            ShowErrorLog(f"Parse Error for {skill_name}: {e}")
            return {"err": str(e)}

# --- 基礎工具工廠 ---

def get_base_tools(context: SessionContext) -> List[Any]:
    """
    獲取與當前會話綁定的基礎工具清單。
    """
    
    @tool
    def get_server_time() -> str:
        """
        獲取伺服器目前的本地時間 (台北時區 UTC+8)。
        用於需要時間上下文的任務。
        """
        tz_taipei = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(tz_taipei)
        return now.strftime("%Y-%m-%d %H:%M:%S")

    @tool
    def SkillPeek(skill_name: str) -> str:
        """
        檢索特定技能的元數據概要 (JSON)。
        """
        data = SkillParser.parse(skill_name)
        if "err" in data:
            return json.dumps({"status": "error", "message": data["err"]})
        
        meta = data.get("metadata", {})
        metadata_node = meta.get("metadata", {})
        raw_tools = metadata_node.get("tools") or meta.get("tools", [])

        tools_list = []
        for t in raw_tools:
            if isinstance(t, dict) and "name" in t:
                tools_list.append(t["name"])
            elif isinstance(t, str):
                tools_list.append(t)

        result = {
            "name": meta.get("name", skill_name),
            "description": meta.get("description", "No description available."),
            "tools_available": tools_list
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @tool
    def SkillLoad(skill_name: str) -> str:
        """
        正式載入技能並獲取完整使用手冊 (Markdown)。
        這會將技能專屬工具注入當前會話。
        """
        data = SkillParser.parse(skill_name)
        if "err" in data:
            return f"Error loading skill: {data['err']}"
        
        # 更新實例化的 context
        context.load_skill(skill_name)
        ShowLog(f"[技能載入] 會話已載入技能: {skill_name}")
        
        return data.get("body", "Skill loaded, but no detailed documentation found.")

    return [get_server_time, SkillPeek, SkillLoad]
