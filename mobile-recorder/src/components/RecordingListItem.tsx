import React from 'react';
import {StyleSheet, Text, TouchableOpacity, View} from 'react-native';
import type {Recording} from '../types';

const STATUS_LABEL: Record<Recording['status'], string> = {
  recording: 'Recording…',
  processing: 'Processing…',
  transcribing: 'Transcribing…',
  summarizing: 'Summarizing…',
  done: 'Ready',
  error: 'Failed',
};

function formatDuration(sec: number | null): string {
  if (sec == null) {
    return '--:--';
  }
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function RecordingListItem({
  recording,
  onPress,
}: {
  recording: Recording;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.row} onPress={onPress}>
      <View style={styles.info}>
        <Text style={styles.title}>{recording.title}</Text>
        <Text style={styles.subtitle}>
          {new Date(recording.createdAt).toLocaleString()} ·{' '}
          {formatDuration(recording.durationSec)}
        </Text>
      </View>
      <Text
        style={[
          styles.status,
          recording.status === 'error' && styles.statusError,
          recording.status === 'done' && styles.statusDone,
        ]}>
        {STATUS_LABEL[recording.status]}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#333',
  },
  info: {flex: 1, marginRight: 12},
  title: {fontSize: 16, fontWeight: '600', color: '#fff'},
  subtitle: {fontSize: 13, color: '#999', marginTop: 2},
  status: {fontSize: 13, color: '#f5a623'},
  statusDone: {color: '#4cd964'},
  statusError: {color: '#ff453a'},
});
