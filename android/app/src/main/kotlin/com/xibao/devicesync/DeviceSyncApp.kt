// DeviceSyncApp.kt
package com.xibao.devicesync

import android.app.Application

class DeviceSyncApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // 還原持久化的通知快取（避免 HyperOS 殺 process 後 cache 清空）
        NotificationCache.init(this)
        // 啟動上傳排程
        DeviceUploadWorker.start(this)
    }
}
