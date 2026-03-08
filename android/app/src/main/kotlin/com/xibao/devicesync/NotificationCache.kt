// NotificationCache.kt
package com.xibao.devicesync

import android.content.Context
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.util.concurrent.CopyOnWriteArrayList

/**
 * 執行緒安全的通知快取，最多保留 100 則。
 * NotificationListenerService 寫入；DataCollector 讀取。
 *
 * 持久化：每次寫入後同步到 SharedPreferences，
 * 確保 HyperOS 殺掉 process 再重啟 WorkManager 後仍能讀到歷史通知。
 */
object NotificationCache {
    private val cache = CopyOnWriteArrayList<NotificationData>()
    private const val MAX_SIZE   = 100
    private const val PREF_NAME  = "notif_cache"
    private const val KEY_NOTIFS = "notifications_json"

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    /**
     * App 啟動時（Application.onCreate 或 Worker.doWork 開頭）呼叫，
     * 從 SharedPreferences 還原上次的通知快取。
     */
    fun init(context: Context) {
        if (cache.isNotEmpty()) return          // 已初始化，跳過
        val stored = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getString(KEY_NOTIFS, null) ?: return
        try {
            val list = json.decodeFromString<List<NotificationData>>(stored)
            cache.addAll(list)
        } catch (_: Exception) { /* 格式損壞，忽略 */ }
    }

    /**
     * 清除已上傳的通知。
     * @param uploadedNotifications 要清除的通知列表（比對 app_package, title, body）
     */
    fun clearUploaded(uploadedNotifications: List<NotificationData>, context: Context? = null) {
        // 移除所有已上傳的通知
        cache.removeAll(uploadedNotifications)
        context?.let { persist(it) }
    }

    fun add(notification: NotificationData, context: Context? = null) {
        val isDuplicate = cache.any {
            it.app_package == notification.app_package &&
            it.title == notification.title &&
            it.body == notification.body
        }
        if (!isDuplicate) {
            cache.add(0, notification)          // 最新的在前
            if (cache.size > MAX_SIZE) cache.removeAt(cache.size - 1)
            context?.let { persist(it) }
        }
    }

    fun remove(appPackage: String, title: String, context: Context? = null) {
        cache.removeIf { it.app_package == appPackage && it.title == title }
        context?.let { persist(it) }
    }

    fun getAll(): List<NotificationData> = cache.toList()

    fun clear() = cache.clear()

    private fun persist(context: Context) {
        try {
            val encoded = json.encodeToString(cache.toList())
            context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
                .edit().putString(KEY_NOTIFS, encoded).apply()
        } catch (_: Exception) {}
    }
}
