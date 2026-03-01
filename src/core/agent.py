#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 核心模組 - 包含 BaseAgent 和 Orchestrator
"""

from typing import List, Any, Dict
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from MyLogger import ShowLog
from src.core.session import SessionContext
from src.core.model_factory import ModelFactory
from src.middleware.context_middleware import ContextInjectedMiddleware
from src.middleware.agent_logging import ToolLoggingMiddleware


class BaseAgent:
    """
    基於會話實例的 Agent 封裝。
    """
    def __init__(self, context: SessionContext, initial_tools: List[Any], model_override: Any = None):
        self.context = context
        self.initial_tools = initial_tools

        # 初始化模型：如果有_override則使用，否則使用預設
        if model_override:
            self.model = model_override
        else:
            self.model = ModelFactory.create_main_model()

        # 建立 Agent 實例，注入 ContextMiddleware
        self.agent = create_agent(
            model=self.model,
            tools=self.initial_tools,
            system_prompt="""你是喜寶，一個強大的 AI 助手。
                請善用工具來完成任務""",
            middleware=[
                ToolLoggingMiddleware(),
                ContextInjectedMiddleware(self.context, self.initial_tools, skill_registry_path="src/skills")
            ]
        )

    def invoke(self, messages: List[Dict[str, Any]]):
        """執行 Agent 邏輯。"""
        return self.agent.invoke({"messages": messages})


class Orchestrator:
    """
    任務協調器。
    負責協調任務處理流程，直接使用 BaseAgent 執行。
    """
    def __init__(self, context: SessionContext, initial_tools: List[Any]):
        self.context = context
        self.initial_tools = initial_tools

    def invoke(self, messages: List[Dict[str, Any]]):
        """
        執行流程：
        直接使用 BaseAgent 處理任務。
        """
        # 建立並執行 Main Agent
        main_agent = BaseAgent(self.context, self.initial_tools)
        ShowLog("[Orchestrator] 使用主模型處理任務")
        return main_agent.invoke(messages)
