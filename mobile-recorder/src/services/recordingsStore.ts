import AsyncStorage from '@react-native-async-storage/async-storage';
import type {Recording} from '../types';

const STORAGE_KEY = '@mobile_recorder/recordings';

type Listener = (recordings: Recording[]) => void;

class RecordingsStore {
  private cache: Recording[] | null = null;
  private listeners = new Set<Listener>();

  async load(): Promise<Recording[]> {
    if (this.cache) {
      return this.cache;
    }
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    this.cache = raw ? (JSON.parse(raw) as Recording[]) : [];
    return this.cache;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    if (this.cache) {
      listener(this.cache);
    }
    return () => this.listeners.delete(listener);
  }

  private async persist() {
    if (!this.cache) {
      return;
    }
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(this.cache));
    this.listeners.forEach(l => l(this.cache!));
  }

  async add(recording: Recording): Promise<void> {
    const list = await this.load();
    this.cache = [recording, ...list];
    await this.persist();
  }

  async update(id: string, patch: Partial<Recording>): Promise<void> {
    const list = await this.load();
    this.cache = list.map(r => (r.id === id ? {...r, ...patch} : r));
    await this.persist();
  }

  async remove(id: string): Promise<void> {
    const list = await this.load();
    this.cache = list.filter(r => r.id !== id);
    await this.persist();
  }

  async get(id: string): Promise<Recording | undefined> {
    const list = await this.load();
    return list.find(r => r.id === id);
  }
}

export const recordingsStore = new RecordingsStore();
