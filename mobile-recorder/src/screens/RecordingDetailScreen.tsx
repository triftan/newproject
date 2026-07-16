import React, {useEffect, useState} from 'react';
import {
  Alert,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStackParamList} from '../navigation/RootNavigator';
import {recordingsStore} from '../services/recordingsStore';
import {processRecording} from '../services/processingPipeline';
import type {Recording} from '../types';

type Props = NativeStackScreenProps<RootStackParamList, 'RecordingDetail'>;

export function RecordingDetailScreen({route, navigation}: Props) {
  const {id} = route.params;
  const [recording, setRecording] = useState<Recording | null>(null);

  useEffect(() => {
    return recordingsStore.subscribe(list => {
      setRecording(list.find(r => r.id === id) ?? null);
    });
  }, [id]);

  if (!recording) {
    return (
      <View style={styles.container}>
        <Text style={styles.empty}>Recording not found.</Text>
      </View>
    );
  }

  const handleShare = () => {
    Share.share({url: recording.filePath, message: recording.filePath});
  };

  const handleRetry = () => {
    processRecording(recording.id);
  };

  const handleDelete = () => {
    Alert.alert('Delete recording?', 'This removes it from the app (the file on disk is left as-is).', [
      {text: 'Cancel', style: 'cancel'},
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await recordingsStore.remove(recording.id);
          navigation.goBack();
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>{recording.title}</Text>
      <Text style={styles.meta}>
        {new Date(recording.createdAt).toLocaleString()}
      </Text>
      <Text style={styles.meta}>File: {recording.filePath || '(pending)'}</Text>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.actionBtn} onPress={handleShare}>
          <Text style={styles.actionText}>Share file</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn} onPress={handleDelete}>
          <Text style={[styles.actionText, styles.destructive]}>Delete</Text>
        </TouchableOpacity>
      </View>

      <Section title="Status" >
        <Text style={styles.body}>{recording.status}</Text>
        {recording.status === 'error' && (
          <>
            <Text style={[styles.body, styles.destructive]}>
              {recording.errorMessage}
            </Text>
            <TouchableOpacity style={styles.retryBtn} onPress={handleRetry}>
              <Text style={styles.actionText}>Retry transcription</Text>
            </TouchableOpacity>
          </>
        )}
      </Section>

      {recording.summary && (
        <Section title="Summary">
          <Text style={styles.body}>{recording.summary}</Text>
        </Section>
      )}

      {recording.transcript && (
        <Section title="Transcript">
          <Text style={styles.body}>{recording.transcript}</Text>
        </Section>
      )}
    </ScrollView>
  );
}

function Section({title, children}: {title: string; children: React.ReactNode}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#000'},
  content: {padding: 20},
  title: {color: '#fff', fontSize: 20, fontWeight: '700'},
  meta: {color: '#999', fontSize: 13, marginTop: 4},
  actions: {flexDirection: 'row', marginTop: 16, gap: 12},
  actionBtn: {
    backgroundColor: '#1c1c1e',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  actionText: {color: '#fff', fontWeight: '600'},
  destructive: {color: '#ff453a'},
  retryBtn: {
    backgroundColor: '#1c1c1e',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginTop: 8,
    alignSelf: 'flex-start',
  },
  section: {marginTop: 24},
  sectionTitle: {color: '#f5a623', fontSize: 13, fontWeight: '700', marginBottom: 6, textTransform: 'uppercase'},
  body: {color: '#ddd', fontSize: 15, lineHeight: 21},
  empty: {color: '#666', textAlign: 'center', marginTop: 40},
});
