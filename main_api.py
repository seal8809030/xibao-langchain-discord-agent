# main_api.py

import os
import sys
import logging

# 確保專案根目錄在路徑中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設定日誌
from MyLogger import ShowLog, setup_logger
script_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
logs_dir = os.path.join(script_dir, 'logs')
setup_logger(script_name, logs_dir, 7)

if __name__ == "__main__":
    import uvicorn
    from src.api import server
    
    port = int(os.getenv("DEVICE_API_PORT", "8766"))
    
    ShowLog(f"啟動 Device API Server 於 port {port}")
    
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
