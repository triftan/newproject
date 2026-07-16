import React, {useEffect, useState} from 'react';
import {
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import {settingsStore} from '../services/settingsStore';

export function SettingsScreen() {
  const [key, setKey] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    settingsStore.getOpenAiKey().then(k => setKey(k ?? ''));
  }, []);

  const handleSave = async () => {
    await settingsStore.setOpenAiKey(key.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const handleClear = async () => {
    await settingsStore.clearOpenAiKey();
    setKey('');
    Alert.alert('Cleared', 'API key removed from device storage.');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>OpenAI API key</Text>
      <Text style={styles.hint}>
        Used to transcribe recordings (Whisper) and generate summaries
        (gpt-4o-mini). Stored locally on this device only — see README for
        swapping this to Keychain/Keystore before shipping.
      </Text>
      <TextInput
        style={styles.input}
        value={key}
        onChangeText={setKey}
        placeholder="sk-..."
        placeholderTextColor="#555"
        autoCapitalize="none"
        autoCorrect={false}
        secureTextEntry
      />
      <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
        <Text style={styles.saveText}>{saved ? 'Saved ✓' : 'Save'}</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.clearBtn} onPress={handleClear}>
        <Text style={styles.clearText}>Clear key</Text>
      </TouchableOpacity>

      <View style={styles.consentBox}>
        <Text style={styles.consentTitle}>Before you record a meeting</Text>
        <Text style={styles.hint}>
          Recording a call's audio without the other participants' knowledge
          is illegal in many places (all-party consent jurisdictions) and
          against most platforms' terms of service, Zoom included. iOS/Android
          both force a persistent recording indicator whenever this app is
          capturing the screen — that's not a bug, it's what keeps this
          compliant. Let people on the call know you're recording.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#000', padding: 20},
  label: {color: '#fff', fontSize: 16, fontWeight: '700', marginBottom: 6},
  hint: {color: '#999', fontSize: 13, lineHeight: 18, marginBottom: 12},
  input: {
    backgroundColor: '#1c1c1e',
    color: '#fff',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    marginBottom: 12,
  },
  saveBtn: {
    backgroundColor: '#2f6fed',
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: 'center',
  },
  saveText: {color: '#fff', fontWeight: '700'},
  clearBtn: {marginTop: 10, alignItems: 'center', paddingVertical: 8},
  clearText: {color: '#ff453a'},
  consentBox: {
    marginTop: 32,
    padding: 14,
    borderRadius: 10,
    backgroundColor: '#1c1c1e',
  },
  consentTitle: {color: '#f5a623', fontWeight: '700', marginBottom: 6},
});
