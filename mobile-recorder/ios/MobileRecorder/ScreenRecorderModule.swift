import AVFoundation
import Foundation
import React

/// Bridges the Broadcast Upload Extension (which does the actual system-wide
/// screen+audio capture — see ../BroadcastExtension/SampleHandler.swift) back
/// to JS. The extension runs as a separate process from this app and can't
/// call into it directly, so the two communicate through:
///   1. A small JSON status file in the shared App Group container.
///   2. A Darwin (cross-process) notification that tells us to go re-read it.
///
/// There is deliberately no `startRecording()`/`stopRecording()` here: Apple
/// only allows a system-wide broadcast to be started by the user's own tap on
/// RPSystemBroadcastPickerView (see BroadcastPickerView.swift) — no app can
/// trigger it programmatically. That restriction exists specifically to
/// prevent silent recording.
@objc(ScreenRecorderModule)
class ScreenRecorderModule: RCTEventEmitter {
    /// Must match the App Group configured in both this target's and the
    /// Broadcast Extension target's "Signing & Capabilities" in Xcode, and
    /// the identifier used in SampleHandler.swift.
    static let appGroupId = "group.com.mobilerecorder.shared"
    static let statusFileName = "broadcast_status.json"
    private static let darwinNotificationName = "com.mobilerecorder.broadcastStatusChanged" as CFString

    override init() {
        super.init()
        CFNotificationCenterAddObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            Unmanaged.passUnretained(self).toOpaque(),
            { _, observer, _, _, _ in
                guard let observer = observer else { return }
                Unmanaged<ScreenRecorderModule>.fromOpaque(observer)
                    .takeUnretainedValue()
                    .refreshFromStatusFile()
            },
            ScreenRecorderModule.darwinNotificationName,
            nil,
            .deliverImmediately
        )
    }

    deinit {
        CFNotificationCenterRemoveObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            Unmanaged.passUnretained(self).toOpaque(),
            CFNotificationName(ScreenRecorderModule.darwinNotificationName),
            nil
        )
    }

    @objc override static func requiresMainQueueSetup() -> Bool { false }

    override func supportedEvents() -> [String]! {
        ["onRecordingStarted", "onRecordingFinished", "onRecordingError"]
    }

    override func startObserving() {}
    override func stopObserving() {}

    private func statusFileURL() -> URL? {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: ScreenRecorderModule.appGroupId)?
            .appendingPathComponent(ScreenRecorderModule.statusFileName)
    }

    /// Re-reads the shared status file and, if it describes a new state,
    /// emits the matching JS event. Safe to call redundantly (e.g. from both
    /// a Darwin notification and JS calling this on app-foreground) since a
    /// "finished"/"error" status is deleted immediately after being emitted.
    @objc func refreshFromStatusFile() {
        guard let url = statusFileURL(),
              let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let status = json["status"] as? String
        else { return }

        switch status {
        case "recording":
            sendEvent(withName: "onRecordingStarted", body: [
                "recordingId": json["recordingId"] as? String ?? "",
                "startedAt": json["startedAt"] as? Double ?? 0,
            ])
        case "finished":
            sendEvent(withName: "onRecordingFinished", body: [
                "recordingId": json["recordingId"] as? String ?? "",
                "filePath": json["filePath"] as? String ?? "",
                "durationSec": json["durationSec"] as? Double ?? 0,
            ])
            try? FileManager.default.removeItem(at: url)
        case "error":
            sendEvent(withName: "onRecordingError", body: [
                "recordingId": json["recordingId"] as? String ?? NSNull(),
                "message": json["message"] as? String ?? "Unknown broadcast error",
            ])
            try? FileManager.default.removeItem(at: url)
        default:
            break
        }
    }

    // MARK: - RN-exposed methods

    @objc func requestPermissions(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter reject: @escaping RCTPromiseRejectBlock
    ) {
        AVAudioSession.sharedInstance().requestRecordPermission { granted in
            DispatchQueue.main.async { resolve(granted) }
        }
    }

    /// Not supported on iOS — see class doc comment. Kept so the unified JS
    /// interface doesn't crash if called; UI should use BroadcastPickerButton.
    @objc func startRecording(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter reject: @escaping RCTPromiseRejectBlock
    ) {
        reject(
            "UNSUPPORTED",
            "iOS requires tapping the system broadcast picker (BroadcastPickerButton) to start recording.",
            nil
        )
    }

    @objc func stopRecording(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter reject: @escaping RCTPromiseRejectBlock
    ) {
        reject(
            "UNSUPPORTED",
            "iOS recordings are stopped via the system picker or the red status-bar timer.",
            nil
        )
    }

    @objc func getLatestBroadcastFile(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter reject: @escaping RCTPromiseRejectBlock
    ) {
        refreshFromStatusFile()
        resolve(NSNull())
    }
}
