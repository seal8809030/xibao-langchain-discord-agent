// ResponseModels.kt
package com.xibao.devicesync

import kotlinx.serialization.Serializable

@Serializable
data class LocationData(
    val latitude: Double,
    val longitude: Double,
    val accuracy_meters: Float? = null,
    val altitude_meters: Double? = null,
    val provider: String? = null,
    val timestamp_iso: String
)

@Serializable
data class BatteryData(
    val level_percent: Int,
    val is_charging: Boolean,
    val charge_source: String,
    val health: String? = null,
    val temperature_celsius: Float? = null
)

@Serializable
data class NotificationData(
    val app_package: String? = null,
    val app_name: String,
    val title: String,
    val body: String,
    val posted_at_iso: String,
    val category: String? = null,
    val is_ongoing: Boolean = false
)

@Serializable
data class DeviceLogRequest(
    val device_id: String,
    val location: LocationData? = null,
    val battery: BatteryData? = null,
    val notifications: List<NotificationData> = listOf()  // 改為非 nullable，預設空陣列
)

@Serializable
data class DeviceBindRequest(
    val device_id: String,
    val token: String,
    val device_name: String? = null
)
