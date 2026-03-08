# refactor/middleware/context_middleware.py

import json
import os
import re
import sys
import importlib.util
from typing import Any, Dict, List, Optional, Callable, Set
from langchain_core.messages import (
    BaseMessage, 
    HumanMessage, 
    SystemMessage, 
    ToolMessage
)
from langchain.agents.middleware import (
    AgentMiddleware, 
    ModelRequest, 
    ModelResponse, 
    ToolCallRequest
)
from MyLogger import ShowLog, ShowErrorLog
from src.core.session import SessionContext

class ContextInjectedMiddleware(AgentMiddleware):
    """
    實例化上下文中間件。
    
    1. 技能發現：注入可用技能列表。
    2. 工具注入：根據 SessionContext.loaded_skill_names 注入工具。
    3. 多模態支援：處理 ResourceRegistry 中的資源。
    """
    
    def __init__(self, context: SessionContext, static_tools: List[Any], skill_registry_path: str = "skills"):
        self.context = context
        self.static_tools = static_tools
        self.skill_registry_path = skill_registry_path
        self._skill_cache: Dict[str, List[Any]] = {}
        
        # 初始日誌：記錄基礎工具清單
        base_names = [getattr(t, 'name', str(t)) for t in static_tools]
        ShowLog(f"[會話隔離] 基礎工具已就緒: {base_names}")

    def _flatten_message(self, message: BaseMessage) -> BaseMessage:
        """
        將多模態訊息內容 (list) 轉換為純文字。
        用於關閉多模態注入時，確保 Agent 收到文字輸入。
        只保留文字區塊，移除多模態區塊。
        """
        content = message.content
        if not content:
            return message

        has_voice = False
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        # 僅保留文字區塊 (包含資源 ID)
                        text_parts.append(block.get("text", ""))
                    elif block_type in ["image_url", "image"]:
                        # 移除圖片區塊，不添加替代文字
                        pass
                    elif block_type == "input_audio":
                        has_voice = True
                        # 移除語音區塊，不添加替代文字
                        pass
                    elif block_type == "media":
                        # 移除媒體區塊，不添加替代文字
                        pass
                elif isinstance(block, str):
                    text_parts.append(block)
            
            # 組合文字內容
            new_text = "\n".join([p for p in text_parts if p]).strip()
            
            # 如果有語音訊息且是 HumanMessage，添加提示給 Router
            if has_voice and isinstance(message, HumanMessage):
                new_text = f"[語音訊息識別需求]\n{new_text}"
            
            # 使用類型動態建立新訊息，保持 ID 和其他屬性
            return message.__class__(content=new_text, **{k: v for k, v in message.additional_kwargs.items()})
        
        return message

    def _discover_skills(self) -> List[Dict[str, str]]:
        skills_metadata = []
        if not os.path.exists(self.skill_registry_path):
            return skills_metadata

        for skill_dir in os.listdir(self.skill_registry_path):
            md_path = os.path.join(self.skill_registry_path, skill_dir, "SKILL.md")
            if os.path.exists(md_path):
                try:
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        match = re.search(r"description:\s*[\"']?(.*?)[\"']?\n", content)
                        desc = match.group(1) if match else "未提供描述。"
                        skills_metadata.append({"name": skill_dir, "description": desc.strip()})
                except Exception as e:
                    ShowErrorLog(f"[技能管理] !! 讀取技能錯誤 {skill_dir}: {e}")
        return skills_metadata

    def _get_skill_tools(self, skill_name: str) -> List[Any]:
        if skill_name in self._skill_cache:
            return self._skill_cache[skill_name]

        tools_path = os.path.join(self.skill_registry_path, skill_name, "tools.py")
        if not os.path.exists(tools_path):
            return []

        # 確保 src 目錄在 sys.path 中
        src_path = os.path.join(os.getcwd(), 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        try:
            spec = importlib.util.spec_from_file_location(f"src.skills.{skill_name}.tools", tools_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                new_tools = module.get_tools(self.context)
                
                ShowLog(f"[技能加載] '{skill_name}' 成功注入 {len(new_tools)} 個工具")
                
                # 💡 注意：因為工具現在與 context 綁定，所以我們不能使用全域 cache
                # 這裡的 cache 應該是針對單次會話的，但由於 Middleware 本身就是單次會話實例的一部分，所以沒問題
                self._skill_cache[skill_name] = new_tools
                return new_tools
        except Exception as e:
            ShowErrorLog(f"[技能錯誤] !! 無法載入技能工具 '{skill_name}': {e}")
        return []

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        messages = list(request.messages)
        
        # 0. 多模態開關控制：如果關閉，則將多模態內容 (list) 轉換為純文字
        if not self.context.is_multimodal_enabled():
            messages = [self._flatten_message(m) for m in messages]
        
        # 1. 技能發現
        skills = self._discover_skills()
        if skills:
            discovery_prompt = (
                "[SYSTEM: Skill Discovery]\n"
                "以下是可用技能。使用 `SkillPeek` 查看詳情或 `SkillLoad` 啟用：\n" + 
                json.dumps(skills, ensure_ascii=False, indent=2)
            )
            messages.insert(0, SystemMessage(content=discovery_prompt))

        # 2. 根據 SessionContext 注入工具
        dynamic_tools = []
        for skill_name in self.context.loaded_skill_names:
            dynamic_tools.extend(self._get_skill_tools(skill_name))
        
        self.context.active_tools = self.static_tools + dynamic_tools
        
        return handler(request.override(messages=messages, tools=self.context.active_tools))

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]) -> Any:
        tool_name = request.tool_call.get("name")
        
        # 尋找對應的工具實體
        target_tool = None
        for t in self.context.active_tools:
            if hasattr(t, 'name') and t.name == tool_name:
                target_tool = t
                break
        
        if target_tool:
            # 執行工具並攔截回傳值
            result = handler(request.override(tool=target_tool))
            
            # 💡 標準化多模態輸出：
            # 如果回傳值是 List 且包含 image_url 字典，將其序列化為 JSON 字串，
            # 確保 Agent 框架能正確將其封裝進 ToolMessage 並傳回給 LLM。
            # 大部分 LangChain ToolHandler 回傳給 LLM 的是 str(result)。
            if isinstance(result, list):
                # 檢查是否含有多模態區塊
                if any(isinstance(b, dict) and b.get("type") in ["image_url", "image"] for b in result):
                    return json.dumps(result, ensure_ascii=False)
            
            return result
        
        return handler(request)
