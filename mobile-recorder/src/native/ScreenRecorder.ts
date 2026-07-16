import {NativeEventEmitter, NativeModules, Platform} from 'react-native';
import type {RecorderEventMap} from '../types';

type ScreenRecorderModuleType = {
  /** Mic permission on both platforms; also POST_NOTIFICATIONS on Android 13+. */
  requestPermissions(): Promise<boolean>;
  /**
   * Android: kicks off the MediaProjection consent dialog, then starts the
   * foreground-service capture automatically once granted. Resolves with
   * the new recording's id.
   *
   * iOS: not implemented here — see <BroadcastPickerButton/>. Apple only
   * allows the user's own tap on the system RPSystemBroadcastPickerView to
   * start a system-wide broadcast; there is no programmatic start.
   */
  startRecording(): Promise<{recordingId: string}>;
  /** Android only. iOS recordings are stopped via the system picker/status bar. */
  stopRecording(): Promise<void>;
  /** iOS only: path of the most recently completed broadcast file, if any. */
  getLatestBroadcastFile?(): Promise<string | null>;
  addListener(eventName: string): void;
  removeListeners(count: number): void;
};

// Native module is undefined until the native code from
// android/.../ScreenRecorderModule.kt or ios/.../ScreenRecorderModule.swift
// is actually built into the app (e.g. running in Jest, or a JS-only bundler
// preview). Fall back to a stub so importing this file never crashes —
// callers get a clear rejected-promise error instead.
const ScreenRecorderModule = NativeModules.ScreenRecorderModule as
  | ScreenRecorderModuleType
  | undefined;

const NOT_LINKED_ERROR =
  'ScreenRecorderModule native module is not available. Build the app ' +
  'through Xcode/Android Studio (not a JS-only bundler) — see README.md.';

const emitter = ScreenRecorderModule ? new NativeEventEmitter(ScreenRecorderModule) : null;

export const screenRecorderEvents = {
  addListener<K extends keyof RecorderEventMap>(
    event: K,
    handler: (payload: RecorderEventMap[K]) => void,
  ) {
    if (!emitter) {
      return () => {};
    }
    const sub = emitter.addListener(event, handler);
    return () => sub.remove();
  },
};

export const ScreenRecorder = {
  requestPermissions: (): Promise<boolean> =>
    ScreenRecorderModule
      ? ScreenRecorderModule.requestPermissions()
      : Promise.reject(new Error(NOT_LINKED_ERROR)),
  startRecording: (): Promise<{recordingId: string}> =>
    ScreenRecorderModule
      ? ScreenRecorderModule.startRecording()
      : Promise.reject(new Error(NOT_LINKED_ERROR)),
  stopRecording: (): Promise<void> =>
    ScreenRecorderModule
      ? ScreenRecorderModule.stopRecording()
      : Promise.reject(new Error(NOT_LINKED_ERROR)),
  getLatestBroadcastFile: (): Promise<string | null> =>
    ScreenRecorderModule?.getLatestBroadcastFile?.() ?? Promise.resolve(null),
  isSystemPickerBased: Platform.OS === 'ios',
};
