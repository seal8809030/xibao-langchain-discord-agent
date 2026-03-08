# Android APK 編譯指南

本文件說明如何使用 Docker 編譯 XiBao DeviceSync Android 應用程式。

## 環境需求

- Docker Desktop (for Windows/Mac/Linux)
- 已安裝 Android 開發相關工具（可透過 Docker 容器取得）

## 編譯步驟

### 1. 確保 Docker 環境正常

請確認 Docker Desktop 已啟動並正常運行。

### 2. 執行 Docker 編譯

在專案根目錄下執行以下命令：

```powershell
# 切換到專案根目錄
cd c:/Code/xibao-langchain-discord-agent

# 執行 Docker 編譯 (使用 android 目錄下的 Dockerfile.build)
docker build -t xibao-android-build -f android/Dockerfile.build android/
```

### 3. 從容器中取出 APK

編譯完成後，APK 會存在於容器內。執行以下命令將 APK 複製到主機：

```powershell
# 複製 APK 到主機的 android 目錄
docker run --rm -v c:/Code/xibao-langchain-discord-agent/android:/output xibao-android-build cp /project/app/build/outputs/apk/debug/app-debug.apk /output/XiBaoDeviceSync-debug.apk
```

### 4. 驗證 APK

檢查 android 目錄是否已生成 APK：

```powershell
# Windows PowerShell
Get-ChildItem android/*.apk
```

成功後會看到類似輸出：
```
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         2026/3/8  下午 12:41     7222254 XiBaoDeviceSync-debug.apk
```

## 常見問題與解決方案

### Q1: Docker build 失敗，出現 "gradlew: No such file or directory"

**原因**：Docker build context 設定錯誤，導致找不到 gradlew 文件。

**解決方案**：確保執行 docker build 時指定正確的 context 為 android 目錄：
```powershell
docker build -t xibao-android-build -f android/Dockerfile.build android/
```

### Q2: 編譯過程卡住或網路超時

**原因**：Gradle 需要下載依賴套件，但網路連接有問題。

**解決方案**：
1. 檢查網路連接
2. 確保 `gradle-wrapper.properties` 中的 `distributionUrl` 指向離線的 gradle-dist.zip (本專案已設定離線模式)
3. 嘗試重新執行編譯

### Q3: 本地端 Gradle 環境問題

**原因**：本地端沒有 Gradle 環境或版本不相容。

**解決方案**：
1. 使用本專案提供的 Docker 環境進行編譯（推薦）
2. 或者確保本地端已安裝 Gradle 8.7 和 Java JDK 21

## 檔案結構說明

- `android/Dockerfile.build`: 用於編譯 Android 專案的 Docker 映像檔定義
- `android/gradle-dist.zip`: Gradle 8.7離線安裝包 (約 127MB)
- `android/gradlew` / `android/gradlew.bat`: Gradle Wrapper 腳本
- `android/app/build.gradle.kts`: App 模組的建置腳本
- `android/XiBaoDeviceSync-debug.apk`: 編譯產出的 Debug APK

## 補充說明

- 本專案使用 `mingc/android-build-box` 作為基礎 Docker 映像檔，內建 Android SDK 和編譯工具。
- 編譯出來的 APK 為 Debug 版本，可直接安裝在 Android 設備上進行測試。
- 若要發布 Release 版本，需要設定正確的 Keystore 和簽署資訊。
