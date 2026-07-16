/**
 * Mobile Recorder — records a screen+audio session (e.g. a Zoom call) via
 * ReplayKit (iOS) / MediaProjection (Android), then transcribes and
 * summarizes it. See README.md for setup and important legal/consent notes.
 *
 * @format
 */

import React from 'react';
import {StatusBar, StyleSheet, useColorScheme, View} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {RootNavigator} from './src/navigation/RootNavigator';

function App() {
  const isDarkMode = useColorScheme() === 'dark';

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <View style={styles.container}>
        <RootNavigator />
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});

export default App;
