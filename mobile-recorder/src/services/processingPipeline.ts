import {recordingsStore} from './recordingsStore';
import {summarizeTranscript, transcribeRecording} from './transcriptionService';

/** Runs transcription + summarization for a finished recording, updating the store as it goes. */
export async function processRecording(recordingId: string): Promise<void> {
  try {
    await recordingsStore.update(recordingId, {status: 'transcribing'});
    const transcript = await transcribeRecording(
      (await recordingsStore.get(recordingId))!.filePath,
    );
    await recordingsStore.update(recordingId, {transcript, status: 'summarizing'});

    const summary = await summarizeTranscript(transcript);
    await recordingsStore.update(recordingId, {summary, status: 'done'});
  } catch (err) {
    await recordingsStore.update(recordingId, {
      status: 'error',
      errorMessage: err instanceof Error ? err.message : String(err),
    });
  }
}
