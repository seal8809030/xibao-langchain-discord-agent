// DataCollector.kt
package com.xibao.devicesync

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.location.Location
import android.os.BatteryManager
import android.os.Build
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.Tasks
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * 負責同步收集 Location、Battery、Notifications 資料。
 * 在 WorkManager 的背景執行緒中呼叫，不可在主執行緒使用。
 */
object DataCollector {

    private val formatter = DateTimeFormatter.ISO_OFFSET_DATE_TIME
        .withZone(ZoneId.systemDefault())

    /** 取得目前 GPS 位置（同步，最長等待 5 秒）。*/
    fun collectLocation(context: Context): LocationData? {
        return try {
            val client = LocationServices.getFusedLocationProviderClient(context)
            val task = client.getCurrentLocation(
                Priority.PRIORITY_BALANCED_POWER_ACCURACY,
                null
            )
            val location: Location? = Tasks.await(task, 5, java.util.concurrent.TimeUnit.SECONDS)
            location?.let {
                val ts = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    formatter.format(Instant.ofEpochMilli(it.time))
                } else {
                    java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX").format(java.util.Date(it.time))
                }
                LocationData(
                    latitude = it.latitude,
                    longitude = it.longitude,
                    accuracy_meters = it.accuracy,
                    altitude_meters = if (it.hasAltitude()) it.altitude else null,
                    provider = it.provider,
                    timestamp_iso = ts
                )
            }
        } catch (e: Exception) {
            null // 未授予位置權限或 GPS 關閉
        }
    }

    /** 取得電池狀態（不需 Permission）。*/
    fun collectBattery(context: Context): BatteryData {
        val intent = context.registerReceiver(
            null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        )!!

        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
        val levelPercent = if (scale > 0) (level * 100 / scale) else level

        val status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        val isCharging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                         status == BatteryManager.BATTERY_STATUS_FULL

        val plugged = intent.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0)
        val chargeSource = when (plugged) {
            BatteryManager.BATTERY_PLUGGED_AC -> "ac"
            BatteryManager.BATTERY_PLUGGED_USB -> "usb"
            BatteryManager.BATTERY_PLUGGED_WIRELESS -> "wireless"
            else -> "none"
        }

        val health = intent.getIntExtra(BatteryManager.EXTRA_HEALTH, BatteryManager.BATTERY_HEALTH_UNKNOWN)
        val healthStr = when (health) {
            BatteryManager.BATTERY_HEALTH_GOOD -> "good"
            BatteryManager.BATTERY_HEALTH_OVERHEAT -> "overheat"
            BatteryManager.BATTERY_HEALTH_DEAD -> "dead"
            BatteryManager.BATTERY_HEALTH_COLD -> "cold"
            else -> "unknown"
        }

        val temp = intent.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) / 10f

        return BatteryData(
            level_percent = levelPercent,
            is_charging = isCharging,
            charge_source = chargeSource,
            health = healthStr,
            temperature_celsius = temp
        )
    }

    /** 取得 NotificationCache 中的所有通知（最多 50 則）。*/
    fun collectNotifications(): List<NotificationData> {
        return NotificationCache.getAll().take(50)
    }
}
