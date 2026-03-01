---
name: discordEventsTools
description: 提供在 Discord 伺服器中建立、修改、刪除、列出活動的功能，包含自動化時間處理。
metadata:
  category: communication
  version: 1.0.0
  tools:
    - name: create_discord_event
      description: 在目前的 Discord 伺服器中建立一個「外部地點」活動。
    - name: update_discord_event
      description: 修改現有的活動資訊 (名稱、描述、時間、地點)。
    - name: get_discord_event
      description: 獲取特定活動的詳細資訊，包括參與人數與連結。
    - name: list_discord_events
      description: 列出伺服器中所有正在進行或即將發生的活動。
    - name: delete_discord_event
      description: 刪除指定的 Discord 活動。
    - name: list_event_users
      description: 列出對該活動按下「感興趣」的成員名單。
---

# Discord 活動管理技能 (Discord Events Skill)

此技能讓 AI 助手能直接操作 Discord 伺服器的活動系統，支援完整的生命週期管理。

## 核心操作規範 (SOP)

1.  **時間處理**：
    *   **重要**：在進行任何時間運算前，必須先調用 `get_server_time` 工具，以確保你擁有準確的台北時間上下文。
    *   將使用者提到的時間（如「明天晚上八點」）精確計算為 ISO 8601 格式。
2.  **回覆準則**：
    *   **親切互動**：建立、更新或查詢成功後，請務必搭配**簡短且親切的問候語**。
    *   **簡明扼要**：回覆中應包含**活動連結 (url)**。由於 Discord 會自動產生預覽卡片，請**不要**在文字中重複描述活動細節（如地點、時間描述等）。
    *   **隱藏細節**：除非使用者要求，否則請勿在回覆中顯示 ID 等技術資訊。
    *   **範例**：
        *   「沒問題，活動已經建立好了，這是連結：[url]」
        *   「活動資訊幫你更新完成囉！✨ [url]」

## 工具清單說明

### 1. `create_discord_event`
- **用途**：建立新的伺服器活動。
- **注意**：預設結束時間為開始時間後的一小時。

### 2. `update_discord_event`
- **用途**：修改現有活動。只需傳入需要變更的欄位即可。

### 3. `list_discord_events`
- **用途**：獲取目前伺服器的活動清單。
- **場景**：當使用者想修改活動但不知道 ID 時，應先執行此工具。

### 4. `get_discord_event` & `list_event_users`
- **用途**：深入了解活動詳情或查看參與名單。

### 5. `delete_discord_event`
- **用途**：移除活動。執行前應與使用者進行二次確認。
