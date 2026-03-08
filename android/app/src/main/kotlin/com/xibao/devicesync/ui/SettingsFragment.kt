// SettingsFragment.kt
package com.xibao.devicesync.ui

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.xibao.devicesync.AppPrefs
import com.xibao.devicesync.DeviceUploadWorker
import com.xibao.devicesync.databinding.FragmentSettingsBinding

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        initUI()
        setupListeners()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private fun initUI() {
        val context = context ?: return
        
        // 初始化週期 Slider
        val currentInterval = AppPrefs.getUploadInterval(context)
        binding.sliderInterval.value = currentInterval.toFloat()
        binding.tvIntervalValue.text = "${currentInterval}秒"
        
        // 初始化綁定碼
        val bindCode = AppPrefs.getOrCreateBindCode(context)
        binding.tvBindCode.text = bindCode
        binding.tvBindInstruction.text = "在 Discord 輸入：/bind $bindCode"
    }

    private fun setupListeners() {
        val context = context ?: return
        
        // 手動同步
        binding.btnManualSync.setOnClickListener {
            DeviceUploadWorker.triggerManualSync(context)
            Toast.makeText(context, "已觸發立即同步", Toast.LENGTH_SHORT).show()
        }

        // 週期 Slider
        binding.sliderInterval.addOnChangeListener { _, value, fromUser ->
            if (fromUser) {
                val newInterval = value.toInt()
                AppPrefs.setUploadInterval(context, newInterval)
                binding.tvIntervalValue.text = "${newInterval}秒"
                // 重新排程 Worker
                DeviceUploadWorker.scheduleNext(context, newInterval)
                Toast.makeText(context, "上傳週期已調整為 ${newInterval} 秒", Toast.LENGTH_SHORT).show()
            }
        }

        // 快捷週期按鈕
        binding.btnInterval10.setOnClickListener { setInterval(10) }
        binding.btnInterval30.setOnClickListener { setInterval(30) }
        binding.btnInterval60.setOnClickListener { setInterval(60) }
        binding.btnInterval300.setOnClickListener { setInterval(300) }

        // 複製綁定碼
        binding.btnCopyCode.setOnClickListener {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val bindCode = AppPrefs.getOrCreateBindCode(context)
            clipboard.setPrimaryClip(ClipData.newPlainText("XiBao 綁定碼", bindCode))
            Toast.makeText(context, "已複製：$bindCode", Toast.LENGTH_SHORT).show()
        }

        // 通知存取設定
        binding.btnNotificationAccess.setOnClickListener {
            openNotificationAccessWithGuidance()
        }
    }

    private fun setInterval(seconds: Int) {
        val context = context ?: return
        AppPrefs.setUploadInterval(context, seconds)
        binding.sliderInterval.value = seconds.toFloat()
        binding.tvIntervalValue.text = "${seconds}秒"
        DeviceUploadWorker.scheduleNext(context, seconds)
        Toast.makeText(context, "上傳週期已調整為 $seconds 秒", Toast.LENGTH_SHORT).show()
    }

    private fun refreshStatus() {
        val context = context ?: return
        
        val hasLocation = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        val hasNotification = isNotificationListenerEnabled()
        val isServiceAlive = AppPrefs.isNotifServiceAlive(context)
        val cachedCount = AppPrefs.getCachedNotifCount(context)

        binding.tvStatusLocation.text =
            if (hasLocation) "✅ 位置權限：已授予" else "❌ 位置權限：未授予"
        binding.tvStatusNotification.text =
            if (hasNotification) "✅ 通知存取：已授予" else "❌ 通知存取：未授予"
        
        binding.tvStatusService.text =
            if (isServiceAlive) "✅ 監聽服務：執行中" else "❌ 監聽服務：未啟動"
        
        binding.tvCachedNotifs.text = "📬 待上傳通知：$cachedCount 則"

        binding.btnNotificationAccess.isEnabled = !hasNotification
        binding.btnNotificationAccess.alpha = if (hasNotification) 0.5f else 1.0f
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val flat = Settings.Secure.getString(requireContext().contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(requireContext().packageName)
    }

    private fun openNotificationAccessWithGuidance() {
        if (isNotificationListenerEnabled()) {
            Toast.makeText(context, "通知存取已開啟", Toast.LENGTH_SHORT).show()
            return
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            AlertDialog.Builder(requireContext())
                .setTitle("開啟通知存取（兩步驟）")
                .setMessage(
                    "Android 安全政策限制從商店外安裝的 App 存取通知，\n" +
                    "需先手動解除限制：\n\n" +
                    "① 長按桌面「XiBao」圖示\n" +
                    "② 點「應用程式資訊」\n" +
                    "③ 右上角 ⋮ →「允許受限設定」\n" +
                    "   小米／HyperOS：設定 → 特殊應用程式存取\n" +
                    "   → 通知使用權 → 找到 XiBao → 允許\n\n" +
                    "④ 返回此畫面，再點「前往通知存取設定」"
                )
                .setPositiveButton("前往應用程式資訊") { _, _ -> openAppInfo() }
                .setNegativeButton("前往通知存取設定") { _, _ -> openNotificationListenerSettings() }
                .show()
        } else {
            openNotificationListenerSettings()
        }
    }

    private fun openAppInfo() {
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", requireContext().packageName, null)
            })
        } catch (e: Exception) {
            openNotificationListenerSettings()
        }
    }

    private fun openNotificationListenerSettings() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS).apply {
                    putExtra(
                        Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME,
                        android.content.ComponentName(
                            requireContext().packageName,
                            com.xibao.devicesync.SyncNotificationListenerService::class.java.name
                        ).flattenToString()
                    )
                })
            } else {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            }
        } catch (e: Exception) {
            try {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            } catch (e2: Exception) {
                Toast.makeText(
                    context,
                    "請手動前往 設定 → 特殊應用程式存取 → 通知使用權",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
}