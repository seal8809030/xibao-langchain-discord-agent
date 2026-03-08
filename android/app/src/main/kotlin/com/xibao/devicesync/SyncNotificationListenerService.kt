// SyncNotificationListenerService.kt
package com.xibao.devicesync

import android.app.Notification
import android.content.pm.PackageManager
import android.os.Build
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * 監聽系統通知，寫入 NotificationCache。
 * 需在系統設定 → 通知存取 中手動授權。
 */
class SyncNotificationListenerService : NotificationListenerService() {

    private val formatter = DateTimeFormatter.ISO_OFFSET_DATE_TIME
        .withZone(ZoneId.systemDefault())

    override fun onListenerConnected() {
        super.onListenerConnected()
        AppPrefs.setNotifServiceAlive(this, true)
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        AppPrefs.setNotifServiceAlive(this, false)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        // 過濾系統低優先通知與 ongoing 通知（如播放器狀態列）
        val extras = sbn.notification.extras ?: return
        val title = extras.getString(Notification.EXTRA_TITLE) ?: return
        val body = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""

        if (title.isBlank() && body.isBlank()) return

        val postedAt = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            formatter.format(Instant.ofEpochMilli(sbn.postTime))
        } else {
            java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX").format(java.util.Date(sbn.postTime))
        }

        val data = NotificationData(
            app_package = sbn.packageName,
            app_name = getAppName(sbn.packageName),
            title = title,
            body = body,
            posted_at_iso = postedAt,
            category = sbn.notification.category,
            is_ongoing = sbn.isOngoing
        )
        NotificationCache.add(data, context = this)
        AppPrefs.setCachedNotifCount(this, NotificationCache.getAll().size)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras ?: return
        val title = extras.getString(Notification.EXTRA_TITLE) ?: return
        NotificationCache.remove(sbn.packageName, title, context = this)
        AppPrefs.setCachedNotifCount(this, NotificationCache.getAll().size)
    }

    private fun getAppName(packageName: String): String {
        return try {
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            packageName
        }
    }
}
