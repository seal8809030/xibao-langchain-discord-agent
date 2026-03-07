---
name: mobileTools
description: 透過 SQL 查詢已綁定用戶的手機資料（GPS、電池、通知等）。每個 Discord 用戶只能查詢自己已綁定的裝置資料。
metadata:
  category: device_query
  version: 2.0.0
  tools:
    - name: query_device_data
      description: 執行 SQLite 查詢獲取手機資料。AI 需自行組裝 SQL，系統會強制注入 user_id 過濾條件確保隱私。
---

# 手機裝置查詢技能 (Mobile Tools Skill)

此技能讓 AI 助手能透過 SQL 查詢使用者 Android 手機的即時狀態。
手機需安裝 **XiBao DeviceSync** App，並在 Discord 使用 `/bind <MAC>` 指令完成裝置綁定。

**重要：每個 Discord 用戶只能查詢自己已綁定的裝置，資料完全隔離。**

---

## 裝置綁定流程 (新)

1. 在手機安裝 **XiBao DeviceSync** App
2. 打開 App → 取得手機的 MAC 位址 (如 `AA:BB:CC:DD:EE:FF`)
3. 在 Discord 輸入：`/bind AA:BB:CC:DD:EE:FF`
4. 回覆「✅ 裝置綁定成功」後即可使用

---

## 資料表結構

### devices (設備狀態)
- `device_id` (TEXT): MAC Address (PK)
- `device_name` (TEXT)
- `battery_level` (INTEGER): 0-100
- `is_charging` (INTEGER): 0/1
- `latitude`, `longitude` (REAL)
- `last_seen` (TEXT): ISO8601

### device_bindings (綁定關係)
- `discord_user_id` (TEXT): PK
- `device_id` (TEXT): UNIQUE
- `device_name` (TEXT)
- `bound_at` (TEXT)

### device_logs (歷史日誌)
- `device_id` (TEXT)
- `log_type` (TEXT): notification/location/battery
- `payload` (TEXT): JSON
- `uploaded_at` (TEXT)

---

## 查詢範例

查詢當前設備:
```sql
SELECT * FROM devices
```

查詢通知:
```sql
SELECT l.* FROM device_logs l
JOIN device_bindings b ON l.device_id = b.device_id
WHERE b.discord_user_id = '{user_id}' AND l.log_type = 'notification'
ORDER BY l.uploaded_at DESC LIMIT 20
```

---

## 錯誤處理

若工具回傳 `err` 欄位：
1. 尚未綁定 → 提示用戶使用 `/bind <MAC>` 綁定
2. App 未執行 → 提示開啟 App
3. SQL 錯誤 → 檢查語法
