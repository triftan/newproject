package com.mobilerecorder

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.util.DisplayMetrics
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import java.io.File

/**
 * Foreground service that owns the actual screen+mic capture.
 *
 * It has to be a foreground service with type "mediaProjection" — Android
 * requires this specifically so the OS can keep a persistent notification up
 * the entire time capture is active. That notification is not optional and
 * cannot be suppressed; it's the Android equivalent of iOS's red status-bar
 * timer, and it exists for the same reason (so screen/audio capture can never
 * be silent).
 *
 * Audio is captured from the microphone rather than via
 * AudioPlaybackCaptureConfiguration (Android's "internal audio" API) because
 * Android explicitly excludes USAGE_VOICE_COMMUNICATION streams from
 * playback capture — which is exactly the stream type VoIP apps like Zoom
 * use for call audio. That's a deliberate OS-level anti-silent-call-recording
 * protection, not a gap in this code. Recording via mic (with the phone's
 * speaker on, or picking up both sides of the call) is the same fallback
 * every third-party recorder on Android uses for this case.
 */
class ScreenRecordService : Service() {

    companion object {
        const val ACTION_START = "com.mobilerecorder.action.START"
        const val ACTION_STOP = "com.mobilerecorder.action.STOP"
        const val EXTRA_RESULT_CODE = "resultCode"
        const val EXTRA_RESULT_DATA = "resultData"
        const val EXTRA_RECORDING_ID = "recordingId"
        const val EVENT_RECORDING_FINISHED = "com.mobilerecorder.RECORDING_FINISHED"
        const val EVENT_RECORDING_ERROR = "com.mobilerecorder.RECORDING_ERROR"
        const val EXTRA_FILE_PATH = "filePath"
        const val EXTRA_DURATION_SEC = "durationSec"
        const val EXTRA_ERROR_MESSAGE = "errorMessage"

        private const val CHANNEL_ID = "screen_recording"
        private const val NOTIFICATION_ID = 4200
        private const val TAG = "ScreenRecordService"
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var mediaRecorder: MediaRecorder? = null
    private var outputFile: File? = null
    private var recordingId: String? = null
    private var startedAtMs: Long = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> handleStart(intent)
            ACTION_STOP -> handleStop()
            else -> Log.w(TAG, "Unknown action: ${intent?.action}")
        }
        return START_NOT_STICKY
    }

    private fun handleStart(intent: Intent) {
        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
        val resultData: Intent? = intent.getParcelableExtra(EXTRA_RESULT_DATA)
        recordingId = intent.getStringExtra(EXTRA_RECORDING_ID)

        if (resultData == null) {
            broadcastError("Missing screen-capture consent data")
            stopSelf()
            return
        }

        startForeground(NOTIFICATION_ID, buildNotification())

        try {
            val projectionManager =
                getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            val projection = projectionManager.getMediaProjection(resultCode, resultData)
            mediaProjection = projection

            val metrics = DisplayMetrics()
            val display = (getSystemService(DISPLAY_SERVICE) as DisplayManager).getDisplay(
                android.view.Display.DEFAULT_DISPLAY
            )
            @Suppress("DEPRECATION")
            display.getRealMetrics(metrics)
            val width = metrics.widthPixels
            val height = metrics.heightPixels
            val density = metrics.densityDpi

            val file = File(
                getExternalFilesDir(null),
                "recording-${recordingId}.mp4",
            )
            outputFile = file

            val recorder = MediaRecorder()
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
            recorder.setVideoSource(MediaRecorder.VideoSource.SURFACE)
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            recorder.setVideoEncoder(MediaRecorder.VideoEncoder.H264)
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            recorder.setVideoSize(width, height)
            recorder.setVideoEncodingBitRate(8_000_000)
            recorder.setVideoFrameRate(30)
            recorder.setAudioEncodingBitRate(128_000)
            recorder.setAudioSamplingRate(44_100)
            recorder.setOutputFile(file.absolutePath)
            recorder.prepare()

            virtualDisplay = projection.createVirtualDisplay(
                "MobileRecorderCapture",
                width,
                height,
                density,
                android.hardware.display.DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                recorder.surface,
                null,
                null,
            )

            recorder.start()
            mediaRecorder = recorder
            startedAtMs = System.currentTimeMillis()

            projection.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() {
                    finishRecording()
                }
            }, null)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start capture", e)
            broadcastError(e.message ?: "Failed to start recording")
            stopSelf()
        }
    }

    private fun handleStop() {
        finishRecording()
    }

    private fun finishRecording() {
        val durationSec = ((System.currentTimeMillis() - startedAtMs) / 1000.0)
        try {
            mediaRecorder?.apply {
                stop()
                release()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping recorder (may be too-short recording)", e)
        }
        mediaRecorder = null

        virtualDisplay?.release()
        virtualDisplay = null
        mediaProjection?.stop()
        mediaProjection = null

        val file = outputFile
        val id = recordingId
        if (file != null && id != null) {
            val intent = Intent(EVENT_RECORDING_FINISHED).apply {
                putExtra(EXTRA_RECORDING_ID, id)
                putExtra(EXTRA_FILE_PATH, file.absolutePath)
                putExtra(EXTRA_DURATION_SEC, durationSec)
            }
            LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
        }

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun broadcastError(message: String) {
        val intent = Intent(EVENT_RECORDING_ERROR).apply {
            putExtra(EXTRA_RECORDING_ID, recordingId)
            putExtra(EXTRA_ERROR_MESSAGE, message)
        }
        LocalBroadcastManager.getInstance(this).sendBroadcast(intent)
    }

    private fun buildNotification(): Notification {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Screen recording",
                NotificationManager.IMPORTANCE_LOW,
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Recording your screen")
            .setContentText("Tap to return to Mobile Recorder")
            .setSmallIcon(android.R.drawable.presence_video_online)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        finishRecording()
    }
}
