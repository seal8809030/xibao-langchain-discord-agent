#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型工廠模組 - 統一管理各種 AI 模型的創建，實現低耦合設計
"""

from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from config import (
    AI_API_KEY, AI_API_BASE, AI_MODEL_ID
)


class ModelFactory:
    """
    模型工廠類別 - 負責創建各種類型的 AI 模型實例
    """

    @staticmethod
    def create_main_model() -> Any:
        """
        創建主模型實例 (適用於多模態、圖片分析、複雜推理)
        """
        return ChatGoogleGenerativeAI(
            model=AI_MODEL_ID,
            api_key=AI_API_KEY,
            base_url=AI_API_BASE,
        )
