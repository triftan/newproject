import AsyncStorage from '@react-native-async-storage/async-storage';

const OPENAI_KEY_STORAGE = '@mobile_recorder/openai_api_key';

/**
 * NOTE: AsyncStorage is unencrypted on-disk storage. It's fine for local
 * dev, but before shipping this, swap this out for react-native-keychain
 * (iOS Keychain / Android Keystore) so the API key isn't stored in plaintext.
 */
export const settingsStore = {
  async getOpenAiKey(): Promise<string | null> {
    return AsyncStorage.getItem(OPENAI_KEY_STORAGE);
  },
  async setOpenAiKey(key: string): Promise<void> {
    await AsyncStorage.setItem(OPENAI_KEY_STORAGE, key);
  },
  async clearOpenAiKey(): Promise<void> {
    await AsyncStorage.removeItem(OPENAI_KEY_STORAGE);
  },
};
