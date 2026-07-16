import {settingsStore} from './settingsStore';

const WHISPER_URL = 'https://api.openai.com/v1/audio/transcriptions';
const CHAT_URL = 'https://api.openai.com/v1/chat/completions';

/**
 * OpenAI's transcription endpoint accepts mp4/m4a/mp3/wav/webm directly
 * (it strips audio server-side), and caps uploads at 25MB. That's roughly
 * 20-30 minutes of a screen recording depending on resolution/bitrate.
 * Longer meetings need client-side chunking (out of scope for v1) — see
 * README "Known limitations".
 */
export async function transcribeRecording(filePath: string): Promise<string> {
  const apiKey = await settingsStore.getOpenAiKey();
  if (!apiKey) {
    throw new Error(
      'No OpenAI API key set. Add one in Settings to enable transcription.',
    );
  }

  const fileUri = filePath.startsWith('file://') ? filePath : `file://${filePath}`;
  const fileName = filePath.split('/').pop() ?? 'recording.mp4';

  const form = new FormData();
  form.append('file', {
    uri: fileUri,
    name: fileName,
    type: fileName.endsWith('.mov') ? 'video/quicktime' : 'video/mp4',
  } as unknown as Blob);
  form.append('model', 'whisper-1');

  const response = await fetch(WHISPER_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'multipart/form-data',
    },
    body: form,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Transcription failed (${response.status}): ${body}`);
  }

  const json = (await response.json()) as {text: string};
  return json.text;
}

export async function summarizeTranscript(transcript: string): Promise<string> {
  const apiKey = await settingsStore.getOpenAiKey();
  if (!apiKey) {
    throw new Error(
      'No OpenAI API key set. Add one in Settings to enable summaries.',
    );
  }

  const response = await fetch(CHAT_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'system',
          content:
            'You summarize meeting transcripts into concise notes: a 2-3 sentence overview, key discussion points as bullets, and any action items as a checklist. Plain text, no markdown headers.',
        },
        {role: 'user', content: transcript},
      ],
      temperature: 0.3,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Summary failed (${response.status}): ${body}`);
  }

  const json = (await response.json()) as {
    choices: {message: {content: string}}[];
  };
  return json.choices[0]?.message.content ?? '';
}
