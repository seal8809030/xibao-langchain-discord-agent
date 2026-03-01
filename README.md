# xibao - LangChain Discord Agent

一個基於 LangChain 和 Discord.py 的智能 Discord 機器人，整合了多種 AI 技能，包括圖像處理、事件管理與薪資查詢等。

## 功能特性

-   **AI 對話**：支援多輪對話與上下文記憶
-   **圖像處理**：圖片分析與生成
-   **Discord 活動管理**：創建、修改、刪除伺服器活動
-   **薪資查詢**：整合 104 薪資數據庫查詢
-   **Docker 支援**：容器化部署，易於擴展

## 快速開始

1.  複製環境變數模板：
    ```bash
    cp .env.example .env
    ```
2.  編輯 `.env` 文件，填入您的 Discord Bot Token 與 API Keys。
3.  使用 Docker Compose 啟動：
    ```bash
    docker-compose up -d
    ```

## 環境變數

| 變數名 | 說明 |
|--------|------|
| `DISCORD_BOT_TOKEN` | Discord 機器人 Token |
| `AI_API_KEY` | AI 服務 API Key |
| `AI_API_BASE` | AI 服務基底 URL |

## 技術棧

-   Python 3.13
-   LangChain / LangGraph
-   Discord.py
-   Docker & Docker Compose
