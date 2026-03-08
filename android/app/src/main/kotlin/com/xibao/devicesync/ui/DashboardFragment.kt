// DashboardFragment.kt
package com.xibao.devicesync.ui

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import com.xibao.devicesync.AppPrefs
import com.xibao.devicesync.R
import com.xibao.devicesync.databinding.FragmentDashboardBinding
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.Timer
import java.util.TimerTask

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!
    
    private var syncTimer: Timer? = null
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        startTimer()
    }

    override fun onResume() {
        super.onResume()
        refreshUI()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        syncTimer?.cancel()
        _binding = null
    }

    // ── 計時器：每秒刷新倒數與最後上傳時間 ───────────────────────────
    private fun startTimer() {
        syncTimer = Timer()
        syncTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                handler.post { refreshUI() }
            }
        }, 0, 1000)
    }

    private fun refreshUI() {
        refreshCountdown()
        refreshConnectionStatus()
        refreshTodayStats()
        refreshLastSync()
    }

    private fun refreshCountdown() {
        val context = context ?: return
        val nextTs = AppPrefs.getNextUploadTime(context)
        val now = System.currentTimeMillis()
        
        if (nextTs > 0) {
            val remaining = ((nextTs - now) / 1000).coerceAtLeast(0)
            val minutes = remaining / 60
            val seconds = remaining % 60
            
            // 更新倒數文字
            binding.tvCountdown.text = if (minutes > 0) {
                String.format(Locale.getDefault(), "%d:%02d", minutes, seconds)
            } else {
                String.format(Locale.getDefault(), "%02d秒", seconds)
            }
            
            // 更新進度條 (基於週期計算)
            val interval = AppPrefs.getUploadInterval(context)
            val progress = ((remaining.toFloat() / interval) * 100).toInt()
            binding.progressCountdown.progress = progress
        } else {
            binding.tvCountdown.text = "等待中..."
            binding.progressCountdown.progress = 0
        }
    }

    private fun refreshConnectionStatus() {
        val context = context ?: return
        val isConnected = AppPrefs.getConnectionStatus(context)
        
        if (isConnected) {
            binding.tvConnectionStatus.text = "• 已連線"
            binding.tvConnectionStatus.setTextColor(resources.getColor(R.color.success_green, null))
        } else {
            binding.tvConnectionStatus.text = "• 斷線"
            binding.tvConnectionStatus.setTextColor(resources.getColor(R.color.error_red, null))
        }
    }

    private fun refreshTodayStats() {
        val context = context ?: return
        val (success, fail) = AppPrefs.getTodayStats(context)
        
        binding.tvTodaySuccess.text = success.toString()
        binding.tvTodayFail.text = fail.toString()
        binding.tvTodayTotal.text = (success + fail).toString()
    }

    private fun refreshLastSync() {
        val context = context ?: return
        val lastTs = AppPrefs.getLastUploadTime(context)
        
        if (lastTs == 0L) {
            binding.tvLastSyncTime.text = "等待中..."
            binding.tvLastSyncStatus.text = "⏳"
            binding.tvLastSyncData.text = "尚無上傳資料"
        } else {
            val now = System.currentTimeMillis()
            val diffMs = now - lastTs
            val diffSec = diffMs / 1000
            val diffMin = diffSec / 60
            val diffHour = diffMin / 60

            val relativeTime = when {
                diffSec < 60 -> "剛剛"
                diffMin < 60 -> "${diffMin} 分鐘前"
                diffHour < 24 -> "${diffHour} 小時前"
                else -> {
                    val fmt = SimpleDateFormat("MM/dd HH:mm", Locale.getDefault())
                    fmt.format(Date(lastTs))
                }
            }
            
            binding.tvLastSyncTime.text = relativeTime
            
            // 檢查最後上傳是否成功
            val isConnected = AppPrefs.getConnectionStatus(context)
            binding.tvLastSyncStatus.text = if (isConnected) "✅" else "❌"
            
            // 顯示最後一筆資料類型
            val (hasLocation, hasBattery, notificationCount) = AppPrefs.getLastSyncData(context)
            val dataParts = mutableListOf<String>()
            if (hasLocation) dataParts.add("📍 位置")
            if (hasBattery) dataParts.add("🔋 電池")
            if (notificationCount > 0) dataParts.add("📬 $notificationCount 則通知")
            
            binding.tvLastSyncData.text = if (dataParts.isEmpty()) "無資料" else dataParts.joinToString(" + ")
        }
    }
}