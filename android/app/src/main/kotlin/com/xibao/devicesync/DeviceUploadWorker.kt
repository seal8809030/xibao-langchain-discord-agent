// DeviceUploadWorker.kt
package com.xibao.devicesync

import android.content.Context
import androidx.work.*
import kotlinx.coroutines.runBlocking
import java.util.concurrent.TimeUnit

/**
 * WorkManager PeriodicWorker：每 60 秒收集並上傳裝置狀態。
 *
 * WorkManager 最小週期為 15 分鐘（系統限制）。
 * 為達 60 秒上傳，改用 PeriodicWorkRequest 最短週期 15 分鐘
 * 搭配 OneTimeWorkRequest 鏈式排程模擬 60 秒間隔。
 *
 * 實作說明：
 * 本 Worker 每次執行完後，用 enqueueUniqueWork 排程 60 秒後的下一次。
 * 這樣可在省電政策下盡力維持 60 秒頻率，不保證精確。
 */
class DeviceUploadWorker(
    appContext: Context,
    params: WorkerParameters
) : Worker(appContext, params) {

    override fun doWork(): Result {
        val context = applicationContext
        NotificationCache.init(context)     // 確保 HyperOS 重啟 process 後 cache 已還原
        val deviceId = AppPrefs.getDeviceId(context)

        val location = DataCollector.collectLocation(context)
        val battery = DataCollector.collectBattery(context)
        val notifications = DataCollector.collectNotifications()
        AppPrefs.setCachedNotifCount(context, notifications.size)

        val request = DeviceLogRequest(
            device_id = deviceId,
            location = location,
            battery = battery,
            notifications = notifications  // 移除 ifEmpty，直接傳送空陣列也可以讓後端知道
        )

        val success = runBlocking { ApiClient.uploadLog(context, request) }

        // 更新連線狀態與統計
        AppPrefs.setConnectionStatus(context, success)
        
        if (success) {
            AppPrefs.setLastUploadTime(context, System.currentTimeMillis())
            AppPrefs.incrementTodaySuccess(context)
            
            // 儲存最後一筆資料摘要
            AppPrefs.setLastSyncData(
                context,
                location != null,
                battery != null,
                notifications.size
            )
            
            // 上傳成功後清除已上傳的通知，避免重複上傳
            if (notifications.isNotEmpty()) {
                NotificationCache.clearUploaded(notifications, context)
                AppPrefs.setCachedNotifCount(context, NotificationCache.getAll().size)
            }
        } else {
            AppPrefs.incrementTodayFail(context)
        }

        // 無論成功或失敗，根據設定的週期再次排程
        val intervalSec = AppPrefs.getUploadInterval(context)
        scheduleNext(context, intervalSec)

        return if (success) Result.success() else Result.retry()
    }

    companion object {
        private const val WORK_NAME = "xibao_device_upload"

        /** 啟動首次上傳，並建立排程。*/
        fun start(context: Context) {
            val interval = AppPrefs.getUploadInterval(context)
            
            // 設定首次排程的 nextUploadTs
            val nextTs = System.currentTimeMillis() + (interval * 1000L)
            AppPrefs.setNextUploadTime(context, nextTs)

            val request = OneTimeWorkRequestBuilder<DeviceUploadWorker>()
                .setInitialDelay(0, TimeUnit.SECONDS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.KEEP, request)
        }

        /** 立即觸發一次上傳（手動），並重新計算下次排程。 */
        fun triggerManualSync(context: Context) {
            val request = OneTimeWorkRequestBuilder<DeviceUploadWorker>()
                .setInitialDelay(0, TimeUnit.SECONDS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork("${WORK_NAME}_manual", ExistingWorkPolicy.KEEP, request)
        }

        /** 排程 N 秒後的下一次執行。*/
        fun scheduleNext(context: Context, intervalSec: Int = 60) {
            // 讀取目前設定的間隔，如果未設定則預設 60
            val interval = if (intervalSec > 0) intervalSec else AppPrefs.getUploadInterval(context)
            
            val nextTs = System.currentTimeMillis() + (interval * 1000L)
            AppPrefs.setNextUploadTime(context, nextTs)
            
            val request = OneTimeWorkRequestBuilder<DeviceUploadWorker>()
                .setInitialDelay(interval.toLong(), TimeUnit.SECONDS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.REPLACE, request)
        }

        /** 停止所有排程。*/
        fun stop(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
