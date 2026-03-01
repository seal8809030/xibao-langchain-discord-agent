# 使用 uv 官方鏡像作為基礎
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# 設置工作目錄
WORKDIR /app

# 禁用 uv 遙測與編譯字節碼
ENV UV_NO_TELEMETRY=1
ENV UV_COMPILE_BYTECODE=1

# 【重點】將虛擬環境移出掛載區 (/app)，避免與宿主機目錄衝突
# 使 Docker 內的環境獨立於 Windows 宿主機的 .venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# 設置時區預設值 (可透過 docker-compose 覆寫)
ENV TZ=Asia/Taipei

# 複製依賴描述文件並進行初步同步 (優化 Build Cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 安裝系統依賴 (例如 antiword 用於處理舊版 .doc 文件)
RUN apt-get update && apt-get install -y --no-install-recommends \
    antiword \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 複製項目代碼 (注意：.dockerignore 會排除 .env)
COPY . .

# 啟動指令
# 使用系統時區配置並啟動應用程式
CMD ["sh", "-c", "ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && uv run python RunXiBao.py"]
