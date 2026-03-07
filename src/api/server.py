# src/api/server.py
"""
XiBao Device API Server

重構重點：
1. 數據分離：狀態寫入 devices 表，日誌寫入 device_logs 表。
2. 直接以 device_id (MAC) 為核心，無需 Token 中間層。
3. 使用 DeviceStore 類別進行高內聚管理。
"""

import os
import config
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from MyLogger import ShowLog, ShowErrorLog
from src.db.device_store import get_store

app = FastAPI(title="XiBao Device API", version="2.0.0")

# 初始化資料庫 Store (Lazy Load)
def get_db():
    db_path = config.DEVICE_DB_PATH
    return get_store(db_path)


# --- Pydantic Models ---

class LocationPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    altitude_meters: Optional[float] = None
    provider: Optional[str] = None
    timestamp_iso: str

class BatteryPayload(BaseModel):
    level_percent: int
    is_charging: bool
    charge_source: Optional[str] = None
    health: Optional[str] = None
    temperature_celsius: Optional[float] = None

class NotificationPayload(BaseModel):
    app_package: Optional[str] = None
    app_name: str
    title: str
    body: str
    posted_at_iso: str
    category: Optional[str] = None
    is_ongoing: Optional[bool] = False

class DeviceLogRequest(BaseModel):
    device_id: str
    location: Optional[LocationPayload] = None
    battery: Optional[BatteryPayload] = None
    notifications: Optional[List[NotificationPayload]] = None
    device_name: Optional[str] = None  # 用於首次註冊設備名稱


# --- Endpoints ---

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/device/log")
def device_log(req: DeviceLogRequest):
    """
    APK 調用此端點上傳設備狀態。
    
    重構後的邏輯：
    1. 如果攜帶了 battery 或 location，直接更新 devices 表的「當前快照」。
    2. 同時將數據追加到 device_logs 表作為歷史記錄。
    """
    store = get_db()
    written = 0
    
    try:
        # 1. 處理即時狀態 (State Update) - 高頻寫入，確保 AI 永遠拿到最新數據
        state_updates = {}
        if req.battery:
            state_updates['battery_level'] = req.battery.level_percent
            state_updates['is_charging'] = req.battery.is_charging
        if req.location:
            state_updates['latitude'] = req.location.latitude
            state_updates['longitude'] = req.location.longitude
        if req.device_name:
            state_updates['device_name'] = req.device_name
            
        if state_updates or req.device_id:
            # 即使沒有狀態更新，也需要更新 last_seen 以表明設備在線
            store.upsert_device_state(req.device_id, **state_updates)
            ShowLog(f"[API] 設備 {req.device_id[:8]}... 狀態已同步")

        # 2. 處理歷史日誌 (Log Append) - 事件流儲存
        if req.location:
            store.append_log(req.device_id, "location", req.location.model_dump())
            written += 1
        if req.battery:
            store.append_log(req.device_id, "battery", req.battery.model_dump())
            written += 1
        if req.notifications:
            for notif in req.notifications:
                store.append_log(req.device_id, "notification", notif.model_dump())
            written += len(req.notifications)
            
        ShowLog(f"[API] 設備 {req.device_id[:8]}... 上傳 {written} 筆日誌")
        return {"status": "ok", "written": written, "state_synced": True}
        
    except Exception as e:
        ShowErrorLog(f"[API] device_log 失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/device/{device_id}/state")
def get_device_state(device_id: str):
    """供外部系統查詢設備當前狀態"""
    store = get_db()
    state = store.get_device_state(device_id)
    if not state:
        raise HTTPException(status_code=404, detail="Device not found")
    return state


@app.get("/api/user/{discord_user_id}/dashboard")
def get_user_dashboard(discord_user_id: str):
    """
    取得用戶的設備儀表板。
    這是 AI Agent 獲取上下文的主要入口。
    """
    store = get_db()
    dashboard = store.get_user_dashboard(discord_user_id)
    if not dashboard:
        return {"status": "unbound", "message": "請先使用 /bind <MAC> 綁定設備"}
    return dashboard
