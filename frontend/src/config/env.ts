import Constants from 'expo-constants';

type Extra = {
  apiBaseUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  passwordResetRedirectTo?: string;
};

const extra = (Constants.expoConfig?.extra ?? {}) as Partial<Extra>;

function readRequiredValue(value: string | undefined, key: keyof Extra): string {
  if (!value) {
    throw new Error(`Missing required app config value: ${key}`);
  }

  return value;
}

export const env = {
  apiBaseUrl: readRequiredValue(extra.apiBaseUrl, 'apiBaseUrl'),
  supabaseUrl: readRequiredValue(extra.supabaseUrl, 'supabaseUrl'),
  supabaseAnonKey: readRequiredValue(extra.supabaseAnonKey, 'supabaseAnonKey'),
  passwordResetRedirectTo: extra.passwordResetRedirectTo,
};
