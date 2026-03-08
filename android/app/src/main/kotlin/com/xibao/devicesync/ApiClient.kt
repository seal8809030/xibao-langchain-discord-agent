// ApiClient.kt
package com.xibao.devicesync

import android.content.Context
import io.ktor.client.*
import io.ktor.client.engine.android.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.json.Json

/**
 * Ktor HTTP client，負責向 XiBao Device API 上傳資料。
 */
object ApiClient {

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(json)
        }
        engine {
            connectTimeout = 10_000
            socketTimeout = 10_000
        }
    }

    /**
     * 上傳裝置狀態 Log 到 Server。
     * @return true 表示成功 (HTTP 2xx)
     */
    suspend fun uploadLog(context: Context, request: DeviceLogRequest): Boolean {
        val url = "${AppPrefs.getServerUrl(context)}/api/device/log"
        return try {
            val response: HttpResponse = client.post(url) {
                contentType(ContentType.Application.Json)
                setBody(request)
            }
            response.status.isSuccess()
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 向 Server 登記 device_id 與 token（綁定流程第一步）。
     * @return true 表示 Server 已接受
     */
    suspend fun registerBind(context: Context, token: String): Boolean {
        val deviceId = AppPrefs.getDeviceId(context)
        val url = "${AppPrefs.getServerUrl(context)}/api/device/bind"
        return try {
            val response: HttpResponse = client.post(url) {
                contentType(ContentType.Application.Json)
                setBody(DeviceBindRequest(device_id = deviceId, token = token))
            }
            response.status.isSuccess()
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 健康檢查，確認 Server 是否可達。
     */
    suspend fun healthCheck(serverUrl: String): Boolean {
        return try {
            val response: HttpResponse = client.get("$serverUrl/api/health")
            response.status.isSuccess()
        } catch (e: Exception) {
            false
        }
    }
}
