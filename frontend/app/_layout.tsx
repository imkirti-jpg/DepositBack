import '../global.css';
import 'react-native-url-polyfill/auto';

import { Slot, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { AuthProvider, useAuth } from '@/auth/auth-context';
import { QueryProvider } from '@/providers/query-provider';

function InitialLayout() {
  const { user, isAuthInitializing } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isAuthInitializing) {
      return;
    }

    const inAuthGroup = segments[0] === '(auth)';

    if (!user && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (user && inAuthGroup) {
      router.replace('/(tabs)/home');
    }
  }, [user, isAuthInitializing, segments, router]);

  return <Slot />;
}

export default function RootLayout() {
  return (
    <QueryProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <InitialLayout />
      </AuthProvider>
    </QueryProvider>
  );
}
