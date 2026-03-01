# refactor/middleware/agent_logging.py

import json
from typing import Any, Callable, List
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest, ModelRequest, ModelResponse
from MyLogger import ShowLog, ShowErrorLog

class ToolLoggingMiddleware(AgentMiddleware):
    """
    工具調用觀察中間件 (Tool Observability Middleware)。
    專注於工具執行的日誌記錄，將觀察邏輯與業務邏輯分離。
    """

    def _summarize_data(self, obj: Any, max_len: int = 100) -> Any:
        """
        遞迴摘要數據結構以防止日誌氾濫 (Log Flooding)。
        """
        if isinstance(obj, str):
            try:
                # 嘗試解析 JSON 字串以摘要其內容
                data = json.loads(obj)
                return self._summarize_data(data, max_len)
            except (json.JSONDecodeError, TypeError):
                if len(obj) > max_len:
                    return f"str(len={len(obj)})..."
                return obj
        elif isinstance(obj, dict):
            return {k: self._summarize_data(v, max_len) for k, v in obj.items()}
        elif isinstance(obj, list):
            if not obj:
                return "list[]"
            # 摘要列表的第一個元素作為代表
            return f"list(len={len(obj)})[{self._summarize_data(obj[0], max_len) if obj else ''}...]"
        elif obj is None:
            return "None"
        
        return type(obj).__name__

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]) -> Any:
        tool_name = request.tool_call.get("name", "Unknown")
        args_summary = self._summarize_data(request.tool_call.get('args'))
        
        ShowLog(f"[工具調用] -> {tool_name} | 參數: {args_summary}")
        
        try:
            result = handler(request)
            
            # 如果結果是 Message 物件則提取內容，否則直接使用結果
            content = result.content if hasattr(result, 'content') else result
            result_summary = self._summarize_data(content)
            
            ShowLog(f"[工具回傳] <- {tool_name} | 結果: {result_summary}")
            return result
        except Exception as e:
            ShowErrorLog(f"[工具錯誤] !! {tool_name} | {str(e)}")
            raise e