// BootReceiver.kt
package com.xibao.devicesync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * 裝置重開機後自動重啟上傳排程。
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            DeviceUploadWorker.start(context)
        }
    }
}
