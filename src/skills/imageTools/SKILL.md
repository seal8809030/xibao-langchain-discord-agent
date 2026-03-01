---
name: imageTools
description: 負責圖片的生成、編輯、持久化與記憶體管理
metadata:
  category: multimedia
  version: 1.1.0
  tools:
    - name: set_current_image
      description: 手動設定當前正在操作的圖片 ID。
    - name: img_gen
      description: 生成新圖片或編輯現有圖片 (Image-to-Image)。
    - name: img_save
      description: 將記憶體中的圖片實例儲存至本地磁碟路徑。
    - name: img_load
      description: 從磁碟路徑載入圖片至記憶體並獲取控制代碼。
    - name: img_mem
      description: 列出、查看或刪除記憶體中的圖片實例。
---

# Image Tools 技能 (Skill)

此技能為 AI 代理提供強大的圖片處理能力，支援從文字生成圖片、基於現有圖片進行編輯、以及在磁碟與記憶體之間靈活遷移圖片。

## 核心概念

1. **短 ID 參照**：圖片在記憶體中以 8 字元的短 ID (如 `a1b2c3d4`) 標識。
2. **當前圖片狀態 (Current Image)**：系統會自動追蹤「最近一次操作」的圖片 ID。許多工具在執行成功後會自動更新此狀態，方便 Agent 接續操作。
3. **最終顯示機制**：在對話流程結束時，系統會自動檢查「當前圖片狀態」。若其不為空，則會將該圖片顯示給用戶。Agent 應根據任務需求，自行決定是否設定、更新或清除此狀態，以控制最終用戶看見的內容。
4. **按需傳輸**：Agent 只需傳遞 ID，僅在需要「看見」圖片內容時才獲取 Base64 數據。

## 工具清單與定義

### 1. `set_current_image(id: str)`
- **用途**：將特定的圖片 ID 設定為「當前焦點」。
- **場景**：當對話中提到多張圖片，且 Agent 需要切換操作對象時使用。

### 2. `img_gen(prompt: str, input_id: Optional[str] = None)`
- **用途**：從無到有生成圖片，或提供一個圖片 ID 進行局部編輯。
- **自動化**：生成成功後，會自動將新生成的圖片設為「當前圖片」。

### 3. `img_save(id: str, path: str)`
- **用途**：將記憶體中的臨時圖片持久化為本地檔案。
- **自動化**：執行後會將該圖片設為「當前圖片」。

### 4. `img_load(path: str)`
- **用途**：將現有的本地圖片引入 Agent 的工作流。
- **自動化**：載入成功後，會自動將該圖片設為「當前圖片」。

### 5. `img_mem(action: str, id: Optional[str] = None)`
- **用途**：管理記憶體資源與查看狀態。
- **參數 `action`**：
    - `list`：列出所有在線 ID，並標註當前圖片 ID。
    - `view`：重新取得特定 ID 的預覽圖，並將其設為「當前圖片」。
    - `del`：釋放特定圖片佔用的記憶體。若刪除的是當前圖片，則會清除當前圖片狀態。

## LangChain 代理最佳實踐 (Best Practices)

1. **善用當前狀態**：
   Agent 可以透過 `img_mem(action="list")` 隨時確認 `current` 欄位，了解目前操作的重心。
   
2. **記憶體管理準則**：
   當一個工作流（例如：生成 -> 編輯 -> 儲存）完成後，應主動呼叫 `img_mem(action="del")` 釋放不再需要的中間產物。

3. **路徑安全性**：
   提供儲存路徑時，應優先使用專案目錄下的資料夾。

## 範例工作流 (Example Workflow)

1. **偵測需求**：使用者要求處理圖片。
2. **執行操作**：
   - `img_load(path="input.jpg")` -> `id: "img_001"` (此時當前圖片為 img_001)。
   - `img_gen(prompt="增加光影效果", input_id="img_001")` -> `id: "img_002"` (當前圖片更新為 img_002)。
   - `img_save(id="img_002", path="output.png")`。
3. **清理資源**：`img_mem(action="del", id="img_001")`, `img_mem(action="del", id="img_002")`。
