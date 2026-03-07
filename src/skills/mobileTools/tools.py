# src/skills/mobileTools/tools.py
"""
Mobile Tools - 智能資料庫介面工具集

設計理念：
1. AI 是資料庫專家：AI 根據用戶問題自行組裝 SQL。
2. 隱私邊界：所有查詢強制以 discord_user_id 為過濾條件。
3. 低耦合：詳細資訊請參閱 SKILL.md。
"""

from typing import List, Any, TYPE_CHECKING
from langchain_core.tools import tool
from MyLogger import ShowLog, ShowErrorLog

if TYPE_CHECKING:
    from src.core.session import SessionContext


def get_tools(context: "SessionContext") -> List[Any]:
    import sqlite3
    import config
    import os
    
    user_id = context.discord_user_id
    db_path = config.DEVICE_DB_PATH

    @tool
    def query_device_data(sql_query: str) -> dict:
        """
        執行 SQLite 查詢。
        """
        
        if not user_id:
            return {"error": "無法取得 Discord 用戶 ID"}
            
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"]
        query_upper = sql_query.upper()
        for kw in forbidden_keywords:
            if kw in query_upper:
                return {"error": f"安全拒絕：禁止執行 {kw} 語句。"}

        if "WHERE" not in query_upper and "JOIN" not in query_upper:
            if "device_logs" in sql_query.lower():
                sql_query = f"""
                SELECT l.* FROM device_logs l
                JOIN device_bindings b ON l.device_id = b.device_id
                WHERE b.discord_user_id = '{user_id}'
                AND {sql_query}
                """ if "WHERE" not in sql_query else f"""
                SELECT l.* FROM device_logs l
                JOIN device_bindings b ON l.device_id = b.device_id
                WHERE b.discord_user_id = '{user_id}'
                AND {sql_query.split('WHERE', 1)[1]}
                """
        
        ShowLog(f"[mobileTools] AI 執行查詢: {sql_query[:100]}...")
        
        try:
            if not os.path.exists(db_path):
                return {"error": "資料庫尚未初始化，請先綁定裝置。"}

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            conn.close()
            
            results = [dict(row) for row in rows]
            ShowLog(f"[mobileTools] 查詢成功，返回 {len(results)} 筆記錄")
            return {"status": "ok", "count": len(results), "data": results[:100]}
            
        except Exception as e:
            ShowErrorLog(f"[mobileTools] SQL 執行失敗: {e}")
            return {"error": f"SQL 執行失敗: {str(e)}"}

    return [query_device_data]
