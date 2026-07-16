export type RecordingStatus =
  | 'recording'
  | 'processing'
  | 'transcribing'
  | 'summarizing'
  | 'done'
  | 'error';

export interface Recording {
  id: string;
  title: string;
  createdAt: number;
  durationSec: number | null;
  /** Local file path to the recorded .mp4 (Android) or .mov (iOS). */
  filePath: string;
  status: RecordingStatus;
  transcript: string | null;
  summary: string | null;
  errorMessage: string | null;
}

export interface RecorderEventMap {
  onRecordingStarted: {recordingId: string; startedAt: number};
  onRecordingFinished: {
    recordingId: string;
    filePath: string;
    durationSec: number;
  };
  onRecordingError: {recordingId: string | null; message: string};
}
