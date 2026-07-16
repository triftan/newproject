# Mobile Recorder

A React Native app that records the screen + audio of whatever's on your
phone (a Zoom call, in particular), then transcribes and summarizes the
recording. Capture is done via each OS's official screen-broadcast API —
iOS ReplayKit, Android MediaProjection — the same mechanism behind Control
Center's built-in screen recorder and every third-party recorder on either
platform.

## Read this first: what this app can and can't do

- **There is no silent mode, on either platform, and that's not a
  limitation of this code — it's an OS guarantee.** iOS shows a persistent
  red status-bar timer and Android shows a persistent notification the
  entire time capture is running. Neither can be hidden, delayed, or
  suppressed by an app. This is deliberate: it's Apple's and Google's
  anti-covert-recording protection.
- **Get consent before recording a call.** Recording another person's audio
  without their knowledge is illegal in many places (all-party-consent
  jurisdictions) and against most platforms' terms of service, Zoom
  included. Tell the people on the call you're recording — the in-app
  Settings screen has a reminder, but it's on you to actually do it.
- **Android audio is captured from the microphone**, not Zoom's internal
  audio stream. Android's internal-audio-capture API
  (`AudioPlaybackCaptureConfiguration`) explicitly excludes
  `USAGE_VOICE_COMMUNICATION`-tagged audio — the category VoIP apps like
  Zoom use — specifically to prevent silent call recording. So this records
  whatever's audible near the phone's mic (the call audio playing through
  the speaker, plus your own voice), same as enabling "Microphone" in iOS's
  Control Center recorder.
- **iOS audio is captured from Zoom's app audio directly** (ReplayKit's
  `.audioApp` sample buffer type), which does include remote participants,
  since Apple's restriction here is "user must tap to start," not "some
  apps' audio is off-limits."

## How capture actually works per platform

| | iOS | Android |
|---|---|---|
| API | ReplayKit `RPSystemBroadcastPickerView` + Broadcast Upload Extension | `MediaProjection` + foreground `Service` |
| Who starts it | **User must tap the system picker control** (`BroadcastPickerButton`) — no app can start this programmatically | App calls `ScreenRecorder.startRecording()`, which shows the OS consent dialog, then starts automatically once granted |
| Where capture runs | A separate extension process (`ios/BroadcastExtension/SampleHandler.swift`), independent of the main app | Inside the app's own foreground service (`ScreenRecordService.kt`) |
| How the main app finds out | Shared App Group file + Darwin (cross-process) notification | In-process `LocalBroadcastManager` event |
| Audio source | Zoom's app audio output (`.audioApp`) | Device microphone |

This asymmetry isn't a shortcut — it's the actual shape of both platforms'
APIs. Any app that does system-wide screen recording on iOS works this way.

## Project layout

```
mobile-recorder/
  App.tsx, src/                    RN/TS app (screens, navigation, storage, pipeline)
    native/ScreenRecorder.ts       unified JS interface over both native modules
    native/BroadcastPickerButton.tsx  iOS system picker wrapper (renders nothing on Android)
    services/                      recordings store, settings/API key store,
                                    transcription + summary pipeline
  android/app/src/main/java/com/mobilerecorder/
    ScreenRecorderModule.kt        RN bridge: permissions, start/stop, events
    ScreenRecordService.kt         foreground service doing the actual capture
  ios/MobileRecorder/
    ScreenRecorderModule.swift     RN bridge: permissions, status polling, events
    BroadcastPickerView.swift      RPSystemBroadcastPickerView wrapper
    *Bridge.m / *Manager.m         Objective-C shims RN needs to export Swift classes
  ios/BroadcastExtension/
    SampleHandler.swift            the actual iOS capture engine (separate target)
```

## Setup

### 1. Install JS deps

```bash
cd mobile-recorder
npm install
```

Already verified in this environment: `npx tsc --noEmit`, `npx eslint src App.tsx`,
and `npx jest` all pass. What has **not** been verified here, because this
build environment has no Xcode, no iOS Simulator, and no Android
emulator/device: actually compiling and running the native Kotlin/Swift code
below. Do that on your own machine before trusting it end to end.

### 2. Android

```bash
cd android && ./gradlew assembleDebug   # sanity-check the native build
cd .. && npx react-native run-android   # or open android/ in Android Studio
```

Nothing else to configure — permissions and the service are already declared
in `AndroidManifest.xml`, and `ScreenRecorderPackage` is registered in
`MainApplication.kt`.

### 3. iOS

The Broadcast Upload Extension is a **separate Xcode target**, and creating
a new target isn't something that can be done by editing files — it has to
happen in Xcode itself:

1. `cd ios && pod install`, then open `MobileRecorder.xcworkspace` in Xcode.
2. **File → New → Target → Broadcast Upload Extension**, name it
   `BroadcastExtension`. Xcode will scaffold its own `SampleHandler.swift` —
   **delete that** and add the real one at `ios/BroadcastExtension/SampleHandler.swift`
   to the new target instead (drag it in, check "BroadcastExtension" as its
   target membership). Do the same for `Info.plist` and
   `BroadcastExtension.entitlements` in that folder (Xcode may generate its
   own versions of these — replace them with the provided ones, or merge the
   `NSExtension` keys / App Group entry in).
3. Select the **MobileRecorder** app target → Signing & Capabilities → **+
   Capability → App Groups** → add `group.com.mobilerecorder.shared`. Repeat
   for the **BroadcastExtension** target with the *same* group ID. (Xcode
   generates/links the entitlements files for you when you do this through
   the UI — that's more reliable than the placeholder `.entitlements` files
   already in the repo, which are there for reference/diffing.)
4. In `ios/MobileRecorder/BroadcastPickerView.swift`, confirm
   `preferredExtension` matches your actual extension bundle ID (defaults to
   `com.mobilerecorder.app.BroadcastExtension` — update if your bundle ID
   prefix differs).
5. Build & run on a **physical device** (ReplayKit broadcast extensions
   don't work in the Simulator).

The four Swift/Obj-C files under `ios/MobileRecorder/` are already wired
into the main app target's build (verified by round-tripping
`project.pbxproj` through the `xcode` npm package — the file references and
Sources build phase entries are in place). Only the extension target itself
needs manual creation.

### 4. Configure transcription

Open the app → Settings → paste an OpenAI API key. Used for:
- `whisper-1` to transcribe the recording (audio extracted server-side from
  the uploaded `.mp4`/`.mov`, capped at 25MB — roughly 20-30 min of footage;
  longer meetings need client-side chunking, not implemented here).
- `gpt-4o-mini` to turn the transcript into a summary + action items.

The key is stored in `AsyncStorage` (plaintext on disk) for now — swap
`src/services/settingsStore.ts` to use `react-native-keychain` before
shipping this anywhere real.

## Known limitations / things to check on a real device

- **Not build/run-tested.** All the JS-level checks pass; the native Kotlin
  and Swift code has not been compiled or run, because this sandbox has
  neither an Android SDK/emulator nor Xcode/iOS Simulator available. Expect
  to fix small build issues (Gradle/CocoaPods versions, signing) on first
  build.
- **Android 14+ foreground service rules**: `FOREGROUND_SERVICE_MEDIA_PROJECTION`
  must be requested at runtime immediately before starting the projection
  (already done in `ScreenRecorderModule.startRecording`), or the service
  will be killed by the OS.
- **iOS mic + app audio mixing** isn't implemented — `SampleHandler.swift`
  only writes `.audioApp`. If you need the local mic voice baked into the
  same track, see the `TODO` there.
- **25MB transcription cap** — see above. For long meetings, chunk the
  audio client-side (e.g. with `ffmpeg-kit-react-native`) before upload.
- **No playback in-app** — the detail screen shares the raw file via the OS
  share sheet rather than embedding a video player, to avoid pulling in
  another native dependency. Add `react-native-video` if you want that.
