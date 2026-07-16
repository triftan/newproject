import AVFoundation
import ReplayKit

/// The actual capture engine on iOS. This runs as a separate, sandboxed
/// process that iOS launches when the user taps "Start Broadcast" on the
/// system picker (BroadcastPickerView in the main app) — it is NOT part of
/// the main app process, which is why it talks back to the app via a shared
/// App Group file + Darwin notification instead of a normal RN bridge call.
///
/// Audio: only `.audioApp` (the sound the device is playing — i.e. Zoom's
/// call audio, which includes remote participants) is written. `.audioMic`
/// buffers also arrive if the user enabled the mic toggle in the picker, but
/// mixing two live audio tracks into one correctly (resampling + summing)
/// is nontrivial and out of scope for this reference implementation; see the
/// TODO below if you need the local mic voice baked in too.
class SampleHandler: RPBroadcastSampleHandler {
    private static let appGroupId = "group.com.mobilerecorder.shared"
    private static let statusFileName = "broadcast_status.json"
    private static let darwinNotificationName = "com.mobilerecorder.broadcastStatusChanged" as CFString

    private var assetWriter: AVAssetWriter?
    private var videoInput: AVAssetWriterInput?
    private var audioInput: AVAssetWriterInput?
    private var sessionStarted = false
    private var recordingId = UUID().uuidString
    private var startedAt = Date()
    private var outputURL: URL?

    override func broadcastStarted(withSetupInfo setupInfo: [String: NSObject]?) {
        recordingId = UUID().uuidString
        startedAt = Date()
        sessionStarted = false

        guard let containerURL = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: Self.appGroupId
        ) else {
            finishBroadcast(with: broadcastError("App Group container is not configured."))
            return
        }

        let fileURL = containerURL.appendingPathComponent("recording-\(recordingId).mov")
        try? FileManager.default.removeItem(at: fileURL)
        outputURL = fileURL

        do {
            let writer = try AVAssetWriter(outputURL: fileURL, fileType: .mov)

            let videoSettings: [String: Any] = [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: Int(UIScreen.main.bounds.width * UIScreen.main.scale),
                AVVideoHeightKey: Int(UIScreen.main.bounds.height * UIScreen.main.scale),
            ]
            let vInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
            vInput.expectsMediaDataInRealTime = true

            let audioSettings: [String: Any] = [
                AVFormatIDKey: kAudioFormatMPEG4AAC,
                AVNumberOfChannelsKey: 2,
                AVSampleRateKey: 44100,
                AVEncoderBitRateKey: 128000,
            ]
            let aInput = AVAssetWriterInput(mediaType: .audio, outputSettings: audioSettings)
            aInput.expectsMediaDataInRealTime = true

            if writer.canAdd(vInput) { writer.add(vInput) }
            if writer.canAdd(aInput) { writer.add(aInput) }

            assetWriter = writer
            videoInput = vInput
            audioInput = aInput

            writeStatus(status: "recording", extra: ["startedAt": startedAt.timeIntervalSince1970])
        } catch {
            finishBroadcast(with: error)
        }
    }

    override func processSampleBuffer(_ sampleBuffer: CMSampleBuffer, with sampleBufferType: RPSampleBufferType) {
        guard let writer = assetWriter, CMSampleBufferDataIsReady(sampleBuffer) else { return }

        if !sessionStarted {
            writer.startWriting()
            writer.startSession(atSourceTime: CMSampleBufferGetPresentationTimeStamp(sampleBuffer))
            sessionStarted = true
        }

        switch sampleBufferType {
        case .video:
            if let input = videoInput, input.isReadyForMoreMediaData {
                input.append(sampleBuffer)
            }
        case .audioApp:
            if let input = audioInput, input.isReadyForMoreMediaData {
                input.append(sampleBuffer)
            }
        case .audioMic:
            // TODO: mix into the app-audio track if you need the local
            // speaker's mic voice included too (see class doc comment).
            break
        @unknown default:
            break
        }
    }

    override func broadcastFinished() {
        let duration = Date().timeIntervalSince(startedAt)
        let writer = assetWriter
        let url = outputURL
        let id = recordingId

        videoInput?.markAsFinished()
        audioInput?.markAsFinished()

        let semaphore = DispatchSemaphore(value: 0)
        writer?.finishWriting {
            semaphore.signal()
        }
        // broadcastFinished() must complete synchronously before the
        // extension process is torn down, so we block briefly on the writer.
        _ = semaphore.wait(timeout: .now() + 10)

        if let url = url, writer?.status == .completed {
            writeStatus(status: "finished", extra: [
                "filePath": url.path,
                "durationSec": duration,
            ])
        } else {
            writeStatus(status: "error", extra: [
                "message": "Failed to finalize recording (\(writer?.error?.localizedDescription ?? "unknown"))",
            ])
        }
    }

    private func broadcastError(_ message: String) -> Error {
        NSError(domain: "com.mobilerecorder.BroadcastExtension", code: 1, userInfo: [
            NSLocalizedDescriptionKey: message,
        ])
    }

    private func writeStatus(status: String, extra: [String: Any]) {
        guard let containerURL = FileManager.default.containerURL(
            forSecurityApplicationGroupIdentifier: Self.appGroupId
        ) else { return }

        var payload: [String: Any] = ["status": status, "recordingId": recordingId]
        extra.forEach { payload[$0.key] = $0.value }

        let statusURL = containerURL.appendingPathComponent(Self.statusFileName)
        if let data = try? JSONSerialization.data(withJSONObject: payload) {
            try? data.write(to: statusURL, options: .atomic)
        }

        CFNotificationCenterPostNotification(
            CFNotificationCenterGetDarwinNotifyCenter(),
            CFNotificationName(Self.darwinNotificationName),
            nil, nil, true
        )
    }
}
