import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

type StorageAdapter = {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
};

async function getWebItem(key: string): Promise<string | null> {
  try {
    return globalThis.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

async function setWebItem(key: string, value: string): Promise<void> {
  try {
    globalThis.localStorage?.setItem(key, value);
  } catch {
    // Ignore write failures in restricted browser contexts.
  }
}

async function removeWebItem(key: string): Promise<void> {
  try {
    globalThis.localStorage?.removeItem(key);
  } catch {
    // Ignore remove failures in restricted browser contexts.
  }
}

export const authStorage: StorageAdapter = {
  getItem: (key) => {
    if (Platform.OS === 'web') {
      return getWebItem(key);
    }

    return SecureStore.getItemAsync(key);
  },
  setItem: (key, value) => {
    if (Platform.OS === 'web') {
      return setWebItem(key, value);
    }

    return SecureStore.setItemAsync(key, value);
  },
  removeItem: (key) => {
    if (Platform.OS === 'web') {
      return removeWebItem(key);
    }

    return SecureStore.deleteItemAsync(key);
  },
};
