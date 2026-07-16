import React, {useCallback, useEffect, useState} from 'react';
import {
  Alert,
  FlatList,
  Platform,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import {v4 as uuid} from '../util/uuid';
import type {RootStackParamList} from '../navigation/RootNavigator';
import {recordingsStore} from '../services/recordingsStore';
import {processRecording} from '../services/processingPipeline';
import {ScreenRecorder, screenRecorderEvents} from '../native/ScreenRecorder';
import {BroadcastPickerButton} from '../native/BroadcastPickerButton';
import {RecordingListItem} from '../components/RecordingListItem';
import type {Recording} from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

export function HomeScreen({navigation}: Props) {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    return recordingsStore.subscribe(setRecordings);
  }, []);

  useEffect(() => {
    recordingsStore.load();
  }, []);

  useEffect(() => {
    const offStarted = screenRecorderEvents.addListener(
      'onRecordingStarted',
      () => setIsRecording(true),
    );
    const offFinished = screenRecorderEvents.addListener(
      'onRecordingFinished',
      async ({recordingId, filePath, durationSec}) => {
        setIsRecording(false);
        const existing = await recordingsStore.get(recordingId);
        if (existing) {
          await recordingsStore.update(recordingId, {
            filePath,
            durationSec,
            status: 'processing',
          });
        } else {
          // iOS broadcast extension flow: the recording entry doesn't exist
          // yet because the extension — not this JS — owns start/stop.
          await recordingsStore.add({
            id: recordingId,
            title: `Recording ${new Date().toLocaleString()}`,
            createdAt: Date.now(),
            durationSec,
            filePath,
            status: 'processing',
            transcript: null,
            summary: null,
            errorMessage: null,
          });
        }
        processRecording(recordingId);
      },
    );
    const offError = screenRecorderEvents.addListener(
      'onRecordingError',
      ({message}) => {
        setIsRecording(false);
        Alert.alert('Recording error', message);
      },
    );
    return () => {
      offStarted();
      offFinished();
      offError();
    };
  }, []);

  const handleStartAndroid = useCallback(async () => {
    try {
      const granted = await ScreenRecorder.requestPermissions();
      if (!granted) {
        Alert.alert(
          'Permissions required',
          'Microphone and notification permissions are needed to record.',
        );
        return;
      }
      const recordingId = uuid();
      await recordingsStore.add({
        id: recordingId,
        title: `Recording ${new Date().toLocaleString()}`,
        createdAt: Date.now(),
        durationSec: null,
        filePath: '',
        status: 'recording',
        transcript: null,
        summary: null,
        errorMessage: null,
      });
      await ScreenRecorder.startRecording();
      setIsRecording(true);
    } catch (err) {
      Alert.alert(
        'Could not start recording',
        err instanceof Error ? err.message : String(err),
      );
    }
  }, []);

  const handleStopAndroid = useCallback(async () => {
    await ScreenRecorder.stopRecording();
  }, []);

  return (
    <View style={styles.container}>
      <View style={styles.recordArea}>
        {Platform.OS === 'android' ? (
          <TouchableOpacity
            style={[styles.recordButton, isRecording && styles.recordButtonActive]}
            onPress={isRecording ? handleStopAndroid : handleStartAndroid}>
            <Text style={styles.recordButtonText}>
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.iosPickerRow}>
            <BroadcastPickerButton style={styles.iosPicker} />
            <Text style={styles.iosHint}>
              Tap to start, then switch to Zoom. iOS shows a red status-bar
              timer the whole time it's recording — tap it again (or tap this
              button again) to stop.
            </Text>
          </View>
        )}
      </View>

      <FlatList
        data={recordings}
        keyExtractor={r => r.id}
        renderItem={({item}) => (
          <RecordingListItem
            recording={item}
            onPress={() => navigation.navigate('RecordingDetail', {id: item.id})}
          />
        )}
        ListEmptyComponent={
          <Text style={styles.empty}>No recordings yet.</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#000'},
  recordArea: {
    padding: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#333',
  },
  recordButton: {
    backgroundColor: '#d92626',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  recordButtonActive: {backgroundColor: '#8f1d1d'},
  recordButtonText: {color: '#fff', fontSize: 17, fontWeight: '700'},
  iosPickerRow: {flexDirection: 'row', alignItems: 'center'},
  iosPicker: {marginRight: 16},
  iosHint: {flex: 1, color: '#999', fontSize: 13, lineHeight: 18},
  empty: {color: '#666', textAlign: 'center', marginTop: 40},
});
