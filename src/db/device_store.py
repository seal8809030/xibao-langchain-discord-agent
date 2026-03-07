# src/db/device_store.py
"""
Device Store Module - High Cohesion, Low Coupling Design

核心概念：
1. Devices (State): 設備的「數位分身」，存放最新狀態（電量、位置）。
2. Bindings (Relation): 1:1 獨佔關係，一個用戶同一時間只能觀察一台設備。
3. Logs (History): 歷史事件流，僅保留必要的事件記錄。

設計原則：
- 直接以 device_id (MAC) 為核心。
- 移除中間 Token 機制，改為直接綁定。
- 寫入時分離「狀態更新」與「日誌存檔」，提高效能。
"""

import sqlite3
import json
import os
import secrets
import string
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from dataclasses import dataclass, field

# ============================================================================
# 內部工具 (Utilities)
# ============================================================================

_TZ_UTC = timezone.utc
_TZ_TAIPEI = timezone(timedelta(hours=8))


def _utc_now() -> str:
    return datetime.now(_TZ_UTC).isoformat()


def _generate_pairing_code() -> str:
    """產生 6 碼英數混合配對碼 (如 XB-4829)。"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(chars) for _ in range(4))
    return f"XB-{code}"


# ============================================================================
# 資料傳輸物件 (DTOs)
# ============================================================================

@dataclass
class DeviceState:
    """設備的當前快照 (From 'devices' table)"""
    device_id: str
    device_name: Optional[str]
    battery_level: Optional[int]
    is_charging: Optional[bool]
    latitude: Optional[float]
    longitude: Optional[float]
    last_seen: str
    model_info: Optional[str] = None


@dataclass
class DeviceBinding:
    """設備綁定關係 (From 'device_bindings' table)"""
    discord_user_id: str
    device_id: str
    device_name: str
    bound_at: str


@dataclass
class DeviceLog:
    """歷史日誌條目 (From 'device_logs' table)"""
    id: int
    device_id: str
    log_type: str
    payload: Dict[str, Any]
    uploaded_at: str


# ============================================================================
# 資料庫管理類別 (DeviceStore)
# ============================================================================

class DeviceStore:
    """
    設備資料庫統一管理介面。
    
    採用建構子注入 DB 路徑，確保無隱藏依賴，方便單元測試。
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_schema()
    
    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def _get_conn(self):
        """提供上下文管理器式的事務控制"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # ============================================================================
    # Schema 初始化
    # ============================================================================
    
    def _init_schema(self):
        """初始化資料庫表結構"""
        with self._get_conn() as conn:
            conn.executescript("""
                -- 1. Devices 主表：存放設備的「當前真相」
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,         -- MAC Address as PK
                    device_name TEXT,
                    battery_level INTEGER,
                    is_charging INTEGER DEFAULT 0,
                    latitude REAL,
                    longitude REAL,
                    last_seen TEXT,                    -- UTC ISO8601
                    model_info TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 2. Bindings 關係表：確保 1:1 獨佔關係
                -- Discord_User_ID 為 PK，確保一個用戶只有一個目標
                -- Device_ID 為 UNIQUE，確保一台設備不被多人同時觀察
                CREATE TABLE IF NOT EXISTS device_bindings (
                    discord_user_id TEXT PRIMARY KEY,   -- PK: One user, one device
                    device_id TEXT UNIQUE,             -- Unique: Exclusive lock
                    device_name TEXT,
                    bound_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 建立索引加速查詢
                CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);
                CREATE INDEX IF NOT EXISTS idx_bindings_device ON device_bindings(device_id);
                
                -- 3. Logs 歷史表：存放事件流
                CREATE TABLE IF NOT EXISTS device_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    log_type TEXT NOT NULL,            -- 'notification', 'location', etc.
                    payload TEXT NOT NULL,             -- JSON
                    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 優化常用篩選路徑
                CREATE INDEX IF NOT EXISTS idx_logs_device_type_time 
                    ON device_logs(device_id, log_type, uploaded_at DESC);
            """)

    # ============================================================================
    # 寫入操作 (Write Path)
    # ============================================================================
    
    def upsert_device_state(self, device_id: str, **kwargs):
        """
        更新設備的當前狀態 (State Upsert)。
        這是「寫入真相」的核心方法。
        """
        # 過濾有效欄位
        valid_keys = {
            'device_name', 'battery_level', 'is_charging', 
            'latitude', 'longitude', 'model_info'
        }
        set_clause = ", ".join([f"{k} = :{k}" for k in kwargs if k in valid_keys])
        set_clause += ", last_seen = :last_seen, updated_at = :updated_at"
        
        params = {k: v for k, v in kwargs.items() if k in valid_keys}
        params['device_id'] = device_id
        params['last_seen'] = _utc_now()
        params['updated_at'] = _utc_now()
        
        sql = f"""
            INSERT INTO devices (device_id, {', '.join(params.keys())})
            VALUES (:device_id, {', '.join(':' + k for k in params.keys())})
            ON CONFLICT(device_id) DO UPDATE SET {set_clause}
        """
        
        # SQLite Python 3.24+ supports UPSERT
        # For older versions, we use REPLACE which might reset rowid
        # But since we have explicit PK, REPLACE works as UPSERT here safely
        with self._get_conn() as conn:
            conn.execute(f"""
                INSERT INTO devices (device_id, {', '.join(params.keys())})
                VALUES (:device_id, {', '.join(':' + k for k in params.keys())})
                ON CONFLICT(device_id) DO UPDATE SET {set_clause}
            """, params)

    def append_log(self, device_id: str, log_type: str, payload: dict):
        """追加歷史日誌"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO device_logs (device_id, log_type, payload) VALUES (?, ?, ?)",
                (device_id, log_type, json.dumps(payload, ensure_ascii=False))
            )
            # TODO: 未來可加入 Background Task 進行數據清理，避免影響寫入效能

    # ============================================================================
    # 綁定操作 (Binding Path)
    # ============================================================================
    
    def bind_device(self, discord_user_id: str, device_id: str, device_name: Optional[str] = None) -> bool:
        """
        綁定設備 (1:1 排他性)。
        
        邏輯：
        1. 檢查設備是否已被他人綁定 (UNIQUE constraint)。
        2. 若無，則建立綁定。
        3. 若有，則踢掉舊用戶 (舊用戶需重新綁定)。
        
        注意：SQLite 的 INSERT OR REPLACE 會先刪除舊行，再插入新行。
        這會導致設備的舊綁定者被直接覆蓋，實現了「強行切換」。
        """
        # 先確保設備存在於主表中 (若 APK 尚未上傳過數據)
        self.upsert_device_state(device_id) 
        
        # 執行綁定 (此處利用 SQLite 的 UPSERT 特性實現「踢人」)
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO device_bindings (discord_user_id, device_id, device_name, bound_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(discord_user_id) DO UPDATE SET 
                        device_id = excluded.device_id,
                        device_name = excluded.device_name,
                        bound_at = excluded.bound_at
                """, (discord_user_id, device_id, device_name or f"Device {device_id[:8]}", _utc_now()))
                return True
        except sqlite3.IntegrityError:
            # 理論上被 ON CONFLICT 捕獲，這裡是 fallback
            return False

    def unbind_device(self, discord_user_id: str) -> bool:
        """解除綁定"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM device_bindings WHERE discord_user_id = ?",
                (discord_user_id,)
            )
            return cursor.rowcount > 0

    def get_binding(self, discord_user_id: str) -> Optional[DeviceBinding]:
        """取得某用戶的當前綁定"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM device_bindings WHERE discord_user_id = ?",
                (discord_user_id,)
            ).fetchone()
            if not row:
                return None
            return DeviceBinding(
                discord_user_id=row['discord_user_id'],
                device_id=row['device_id'],
                device_name=row['device_name'],
                bound_at=row['bound_at']
            )

    # ============================================================================
    # 查詢操作 (Read Path)
    # ============================================================================
    
    def get_device_state(self, device_id: str) -> Optional[DeviceState]:
        """取得設備的最新狀態"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM devices WHERE device_id = ?",
                (device_id,)
            ).fetchone()
            if not row:
                return None
            return DeviceState(
                device_id=row['device_id'],
                device_name=row['device_name'],
                battery_level=row['battery_level'],
                is_charging=bool(row['is_charging']),
                latitude=row['latitude'],
                longitude=row['longitude'],
                last_seen=row['last_seen'],
                model_info=row['model_info']
            )

    def get_user_dashboard(self, discord_user_id: str) -> Optional[Dict[str, Any]]:
        """
        取得用戶的儀表板數據 (一次性 JOIN)。
        
        這是 AI 查詢的快速入口，一次性返回：
        - 綁定狀態
        - 設備快照 (電量、位置)
        """
        binding = self.get_binding(discord_user_id)
        if not binding:
            return None
            
        state = self.get_device_state(binding.device_id)
        
        return {
            "binding": binding,
            "state": state,
            "is_online": self._is_recent(state.last_seen) if state else False
        }
    
    def _is_recent(self, last_seen_iso: str, minutes: int = 5) -> bool:
        """簡單判斷設備是否在線 (基於最後上線時間)"""
        try:
            dt = datetime.fromisoformat(last_seen_iso.replace('Z', '+00:00'))
            diff = datetime.now(_TZ_UTC) - dt.replace(tzinfo=_TZ_UTC)
            return diff.total_seconds() < (minutes * 60)
        except:
            return False

    def get_recent_logs(self, device_id: str, log_type: str, limit: int = 20) -> List[DeviceLog]:
        """取得設備的歷史日誌"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM device_logs WHERE device_id = ? AND log_type = ? ORDER BY uploaded_at DESC LIMIT ?",
                (device_id, log_type, limit)
            ).fetchall()
            return [
                DeviceLog(
                    id=r['id'],
                    device_id=r['device_id'],
                    log_type=r['log_type'],
                    payload=json.loads(r['payload']),
                    uploaded_at=r['uploaded_at']
                ) for r in rows
            ]
            
    def get_user_recent_notifications(self, discord_user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        取得該用戶所有綁定設備的近期通知 (目前僅支援單一綁定，未來可擴充為 List)。
        """
        binding = self.get_binding(discord_user_id)
        if not binding:
            return []
            
        logs = self.get_recent_logs(binding.device_id, "notification", limit)
        
        # 格式化輸出
        results = []
        for log in logs:
            data = log.payload
            data["_uploaded_at"] = log.uploaded_at
            data["device_name"] = binding.device_name
            results.append(data)
            
        return results


# ============================================================================
# 便捷單例 (Factory)
# ============================================================================

# 延遲初始化，支援單一實例模式 (避免每次 API 請求都創建新連線)
_store_instance: Optional[DeviceStore] = None

def get_store(db_path: str = "data/devices.db") -> DeviceStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = DeviceStore(db_path)
    return _store_instance
