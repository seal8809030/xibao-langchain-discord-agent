# refactor/skills/salaryTools/tools.py

import os
import sqlite3
import pandas as pd
from typing import List, Any, TYPE_CHECKING
from langchain_core.tools import tool
from MyLogger import ShowLog, ShowErrorLog

if TYPE_CHECKING:
    from src.core.session import SessionContext

# 全域變數用於快取資料庫連接（內存型）
_db_conn = None

def _get_db_connection():
    global _db_conn
    if _db_conn is None:
        try:
            # 建立記憶體中的 SQLite 資料庫
            _db_conn = sqlite3.connect(":memory:", check_same_thread=False)
            
            # 讀取 CSV 並載入至 SQL
            csv_path = "src/skills/salaryTools/104_salary_data.csv"
            if not os.path.exists(csv_path):
                ShowErrorLog(f"CSV file not found: {csv_path}")
                return None
            
            df = pd.read_csv(csv_path)
            # 將資料寫入 salary_data 表
            df.to_sql("salary_data", _db_conn, index=False, if_exists="replace")
        except Exception as e:
            ShowErrorLog(f"Failed to load CSV into SQL: {e}")
            _db_conn = None
            
    return _db_conn

def get_tools(context: "SessionContext") -> List[Any]:
    """
    獲取與會話實例綁定的薪資查詢工具。
    """

    @tool
    def query_salary_db(sql_query: str) -> str:
        """
        使用 SQL 語法查詢公司薪資資料庫。
        資料表名稱為 `salary_data`，包含欄位：`公司名稱` (TEXT), `股票代號` (INT), `非主管年薪中位數(萬)` (INT)。
        例如：SELECT * FROM salary_data WHERE 公司名稱 LIKE '%台積電%'
        """
        conn = _get_db_connection()
        if conn is None:
            return "Error: Database connection failed."
        
        try:
            # 使用 pandas 執行查詢以方便轉為 JSON/Markdown
            df_result = pd.read_sql_query(sql_query, conn)
            
            if df_result.empty:
                return "查無符合條件的資料。"
            
            # 返回 JSON 格式字串
            return df_result.to_json(orient="records", force_ascii=False)
        except Exception as e:
            ShowErrorLog(f"SQL Query Error: {e}")
            return f"SQL 查詢出錯: {str(e)}"

    return [query_salary_db]
