// AppPrefs.kt
package com.xibao.devicesync

import android.content.Context
import android.provider.Settings
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * SharedPreferences 輔助類別。
 *
 * 裝置識別碼：使用 Settings.Secure.ANDROID_ID（Android 系統保證唯一），
 * 格式化為 MAC 地址樣式 XX:XX:XX:XX:XX:XX，語義上等同硬體 MAC。
 * （Android 6+ 起 WifiManager 回傳的 MAC 已被強制隨機化，
 *   無法取得真實硬體 MAC，ANDROID_ID 為業界最佳替代方案。）
 *
 * Server：固定為 IP:Port，不開放 UI 修改。
 */
object AppPrefs {
    private const val PREF_NAME      = "xibao_prefs"
    private const val KEY_DEVICE_ID  = "device_mac_id"   // v2: MAC-format key
    private const val KEY_LAST_UPLOAD = "last_upload_ts"  // epoch ms，最後成功上傳時間
    private const val KEY_UPLOAD_INTERVAL = "upload_interval_sec" // 上傳週期（秒）
    private const val KEY_NEXT_UPLOAD_TS = "next_upload_ts"   // 下一次預定上傳時間（epoch ms）

    // 連線狀態
    private const val KEY_CONNECTION_STATUS = "connection_status"
    
    // 今日統計
    private const val KEY_TODAY_SUCCESS = "today_success_count"
    private const val KEY_TODAY_FAIL = "today_fail_count"
    private const val KEY_STATS_DATE = "stats_date"
    
    // 調試狀態
    private const val KEY_NOTIF_SERVICE_ALIVE = "notif_service_alive"
    private const val KEY_CACHED_NOTIF_COUNT  = "cached_notif_count"

    // 最後一筆資料記錄
    private const val KEY_LAST_HAS_LOCATION = "last_has_location"
    private const val KEY_LAST_HAS_BATTERY = "last_has_battery"
    private const val KEY_LAST_NOTIFICATION_COUNT = "last_notification_count"

    /** 從 BuildConfig 讀取 Server 位址 (由 android/.env 定義) */
    val SERVER_URL = BuildConfig.SERVER_URL

    /**
     * 取得裝置唯一識別碼（MAC 格式：XX:XX:XX:XX:XX:XX）。
     * 以 ANDROID_ID 前 12 個 hex 字符格式化，首次計算後持久儲存。
     */
    fun getDeviceId(context: Context): String {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.getString(KEY_DEVICE_ID, null)?.let { return it }

        // 取 ANDROID_ID（16 hex chars），取前 12 位格式化為 MAC
        val raw = (Settings.Secure.getString(
            context.contentResolver, Settings.Secure.ANDROID_ID
        ) ?: "000000000000")
            .replace(Regex("[^0-9a-fA-F]"), "")
            .take(12)
            .uppercase()
            .padEnd(12, '0')

        val mac = raw.chunked(2).joinToString(":")   // "AB:CD:EF:12:34:56"
        prefs.edit().putString(KEY_DEVICE_ID, mac).apply()
        return mac
    }

    /**
     * 取得（或建立）固定綁定碼（= 裝置 MAC 識別碼）。
     * 首次呼叫時由 ANDROID_ID 計算後持久儲存，後續直接返回儲存值。
     * Discord 綁定指令：/bind XX:XX:XX:XX:XX:XX
     */
    fun getOrCreateBindCode(context: Context): String = getDeviceId(context)

    /** 向下相容舊呼叫，等同 getOrCreateBindCode。 */
    fun getBindCode(context: Context): String = getOrCreateBindCode(context)

    fun getServerUrl(context: Context): String = SERVER_URL

    // ── 最後上傳時間 ─────────────────────────────────────────

    /** 取得最後成功上傳的時間戳（epoch ms），0 表示尚未上傳。 */
    fun getLastUploadTime(context: Context): Long =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getLong(KEY_LAST_UPLOAD, 0L)

    /** 記錄本次成功上傳的時間（由 DeviceUploadWorker 呼叫）。 */
    fun setLastUploadTime(context: Context, timestampMs: Long) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putLong(KEY_LAST_UPLOAD, timestampMs).apply()
    }

    /** 取得上傳週期（秒），預設 60 秒。 */
    fun getUploadInterval(context: Context): Int {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getInt(KEY_UPLOAD_INTERVAL, 60)
    }

    /** 設定上傳週期（秒），並立即重新計算下次上傳時間。 */
    fun setUploadInterval(context: Context, intervalSec: Int) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putInt(KEY_UPLOAD_INTERVAL, intervalSec).apply()
        // 設定新週期後，更新下次上傳時間為現在 + intervalSec
        setNextUploadTime(context, System.currentTimeMillis() + (intervalSec * 1000L))
    }

    /** 取得下一次預定上傳時間（epoch ms），0 表示未排程。 */
    fun getNextUploadTime(context: Context): Long =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getLong(KEY_NEXT_UPLOAD_TS, 0L)

    /** 記錄下一次預定上傳時間。 */
    fun setNextUploadTime(context: Context, timestampMs: Long) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putLong(KEY_NEXT_UPLOAD_TS, timestampMs).apply()
    }
    
    // ── 連線狀態 ─────────────────────────────────────────
    
    /** 取得連線狀態（true = 已連線/false = 斷線） */
    fun getConnectionStatus(context: Context): Boolean =
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_CONNECTION_STATUS, false)
    
    /** 設定連線狀態 */
    fun setConnectionStatus(context: Context, connected: Boolean) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_CONNECTION_STATUS, connected).apply()
    }
    
    // ── 今日統計 ─────────────────────────────────────────
    
    /** 遞增今日成功計數 */
    fun incrementTodaySuccess(context: Context) {
        checkResetDaily(context)
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val current = prefs.getInt(KEY_TODAY_SUCCESS, 0)
        prefs.edit().putInt(KEY_TODAY_SUCCESS, current + 1).apply()
    }
    
    /** 遞增今日失敗計數 */
    fun incrementTodayFail(context: Context) {
        checkResetDaily(context)
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val current = prefs.getInt(KEY_TODAY_FAIL, 0)
        prefs.edit().putInt(KEY_TODAY_FAIL, current + 1).apply()
    }
    
    /** 取得今日統計 (成功, 失敗) */
    fun getTodayStats(context: Context): Pair<Int, Int> {
        checkResetDaily(context)
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        return Pair(
            prefs.getInt(KEY_TODAY_SUCCESS, 0),
            prefs.getInt(KEY_TODAY_FAIL, 0)
        )
    }
    
    /** 檢查並重置每日統計 */
    private fun checkResetDaily(context: Context) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val today = SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())
        val saved = prefs.getString(KEY_STATS_DATE, "")
        
        if (saved != today) {
            prefs.edit()
                .putString(KEY_STATS_DATE, today)
                .putInt(KEY_TODAY_SUCCESS, 0)
                .putInt(KEY_TODAY_FAIL, 0)
                .apply()
        }
    }
    
    // ── 最後一筆資料記錄 ─────────────────────────────────────────
    
    /** 儲存最後一筆資料摘要 */
    fun setLastSyncData(context: Context, hasLocation: Boolean, hasBattery: Boolean, notificationCount: Int) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_LAST_HAS_LOCATION, hasLocation)
            .putBoolean(KEY_LAST_HAS_BATTERY, hasBattery)
            .putInt(KEY_LAST_NOTIFICATION_COUNT, notificationCount)
            .apply()
    }
    
    /** 取得最後一筆資料摘要 (位置, 電池, 通知數) */
    fun getLastSyncData(context: Context): Triple<Boolean, Boolean, Int> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        return Triple(
            prefs.getBoolean(KEY_LAST_HAS_LOCATION, false),
            prefs.getBoolean(KEY_LAST_HAS_BATTERY, false),
            prefs.getInt(KEY_LAST_NOTIFICATION_COUNT, 0)
        )
    }

    // ── 調試狀態 ─────────────────────────────────────────────
    fun setNotifServiceAlive(context: Context, alive: Boolean) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_NOTIF_SERVICE_ALIVE, alive).apply()
    }

    fun isNotifServiceAlive(context: Context): Boolean {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getBoolean(KEY_NOTIF_SERVICE_ALIVE, false)
    }

    fun setCachedNotifCount(context: Context, count: Int) {
        context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .edit().putInt(KEY_CACHED_NOTIF_COUNT, count).apply()
    }

    fun getCachedNotifCount(context: Context): Int {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
            .getInt(KEY_CACHED_NOTIF_COUNT, 0)
    }
}
