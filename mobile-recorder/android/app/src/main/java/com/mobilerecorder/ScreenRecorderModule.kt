package com.mobilerecorder

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.localbroadcastmanager.content.LocalBroadcastManager
import com.facebook.react.bridge.ActivityEventListener
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.bridge.Arguments
import com.facebook.react.modules.core.DeviceEventManagerModule
import com.facebook.react.modules.core.PermissionAwareActivity
import com.facebook.react.modules.core.PermissionListener
import java.util.UUID

class ScreenRecorderModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext), ActivityEventListener {

    companion object {
        const val NAME = "ScreenRecorderModule"
        private const val CAPTURE_REQUEST_CODE = 4201
        private const val PERMISSION_REQUEST_CODE = 4202
    }

    private var pendingRecordingId: String? = null
    private var startPromise: Promise? = null

    init {
        reactContext.addActivityEventListener(this)
        val filter = IntentFilter().apply {
            addAction(ScreenRecordService.EVENT_RECORDING_FINISHED)
            addAction(ScreenRecordService.EVENT_RECORDING_ERROR)
        }
        LocalBroadcastManager.getInstance(reactContext).registerReceiver(receiver, filter)
    }

    override fun getName() = NAME

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ScreenRecordService.EVENT_RECORDING_FINISHED -> {
                    val map: WritableMap = Arguments.createMap().apply {
                        putString(
                            "recordingId",
                            intent.getStringExtra(ScreenRecordService.EXTRA_RECORDING_ID),
                        )
                        putString(
                            "filePath",
                            intent.getStringExtra(ScreenRecordService.EXTRA_FILE_PATH),
                        )
                        putDouble(
                            "durationSec",
                            intent.getDoubleExtra(ScreenRecordService.EXTRA_DURATION_SEC, 0.0),
                        )
                    }
                    emit("onRecordingFinished", map)
                }
                ScreenRecordService.EVENT_RECORDING_ERROR -> {
                    val map: WritableMap = Arguments.createMap().apply {
                        putString(
                            "recordingId",
                            intent.getStringExtra(ScreenRecordService.EXTRA_RECORDING_ID),
                        )
                        putString(
                            "message",
                            intent.getStringExtra(ScreenRecordService.EXTRA_ERROR_MESSAGE)
                                ?: "Unknown recording error",
                        )
                    }
                    emit("onRecordingError", map)
                }
            }
        }
    }

    private fun emit(event: String, map: WritableMap) {
        reactApplicationContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit(event, map)
    }

    @ReactMethod
    fun requestPermissions(promise: Promise) {
        val activity = currentActivity as? PermissionAwareActivity
        if (activity == null) {
            promise.resolve(false)
            return
        }

        val needed = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            needed.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val missing = needed.filter {
            ContextCompat.checkSelfPermission(reactApplicationContext, it) !=
                PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            promise.resolve(true)
            return
        }

        activity.requestPermissions(
            missing.toTypedArray(),
            PERMISSION_REQUEST_CODE,
            PermissionListener { requestCode, _, grantResults ->
                if (requestCode != PERMISSION_REQUEST_CODE) {
                    return@PermissionListener false
                }
                val granted = grantResults.isNotEmpty() &&
                    grantResults.all { it == PackageManager.PERMISSION_GRANTED }
                promise.resolve(granted)
                true
            },
        )
    }

    @ReactMethod
    fun startRecording(promise: Promise) {
        val activity = currentActivity
        if (activity == null) {
            promise.reject("NO_ACTIVITY", "App is not in the foreground")
            return
        }

        pendingRecordingId = UUID.randomUUID().toString()
        startPromise = promise

        val projectionManager =
            reactApplicationContext.getSystemService(Context.MEDIA_PROJECTION_SERVICE)
                as MediaProjectionManager
        activity.startActivityForResult(
            projectionManager.createScreenCaptureIntent(),
            CAPTURE_REQUEST_CODE,
        )
    }

    override fun onActivityResult(activity: Activity?, requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode != CAPTURE_REQUEST_CODE) {
            return
        }
        val id = pendingRecordingId
        val promise = startPromise
        pendingRecordingId = null
        startPromise = null

        if (resultCode != Activity.RESULT_OK || data == null || id == null) {
            promise?.reject("PERMISSION_DENIED", "Screen capture permission was denied")
            return
        }

        val serviceIntent = Intent(reactApplicationContext, ScreenRecordService::class.java).apply {
            action = ScreenRecordService.ACTION_START
            putExtra(ScreenRecordService.EXTRA_RESULT_CODE, resultCode)
            putExtra(ScreenRecordService.EXTRA_RESULT_DATA, data)
            putExtra(ScreenRecordService.EXTRA_RECORDING_ID, id)
        }
        ContextCompat.startForegroundService(reactApplicationContext, serviceIntent)

        val startedMap: WritableMap = Arguments.createMap().apply {
            putString("recordingId", id)
            putDouble("startedAt", System.currentTimeMillis().toDouble())
        }
        emit("onRecordingStarted", startedMap)

        val result: WritableMap = Arguments.createMap().apply { putString("recordingId", id) }
        promise?.resolve(result)
    }

    override fun onNewIntent(intent: Intent?) {}

    @ReactMethod
    fun stopRecording(promise: Promise) {
        val serviceIntent = Intent(reactApplicationContext, ScreenRecordService::class.java).apply {
            action = ScreenRecordService.ACTION_STOP
        }
        reactApplicationContext.startService(serviceIntent)
        promise.resolve(null)
    }

    // Required by NativeEventEmitter on the JS side (no-op: we use LocalBroadcastManager, not JS-driven subscription counts).
    @ReactMethod
    fun addListener(eventName: String) {}

    @ReactMethod
    fun removeListeners(count: Int) {}
}
