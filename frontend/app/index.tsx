import { Redirect } from 'expo-router';

import { useAuth } from '@/auth/auth-context';

export default function Index() {
  const { isAuthInitializing, user } = useAuth();

  if (isAuthInitializing) {
    return null;
  }

  if (user) {
    return <Redirect href="/(tabs)/home" />;
  }

  return <Redirect href="/(auth)/login" />;
}
