import React from 'react';
import {Platform, StyleSheet, View, ViewStyle, requireNativeComponent} from 'react-native';

/**
 * Wraps iOS's RPSystemBroadcastPickerView. This is the ONLY way to start a
 * system-wide (cross-app) screen broadcast on iOS — Apple requires a direct
 * user tap on this exact system-rendered control, so it can't be a normal RN
 * <Button/> that calls a native method. Renders nothing on Android, where
 * MediaProjection lets us start recording from a regular button instead
 * (see ScreenRecorder.startRecording()).
 */
const NativeBroadcastPicker =
  Platform.OS === 'ios'
    ? requireNativeComponent<{style?: ViewStyle}>('BroadcastPickerView')
    : null;

export function BroadcastPickerButton({style}: {style?: ViewStyle}) {
  if (Platform.OS !== 'ios' || !NativeBroadcastPicker) {
    return null;
  }
  return (
    <View style={[styles.wrapper, style]}>
      <NativeBroadcastPicker style={StyleSheet.absoluteFill} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: 64,
    height: 64,
  },
});
