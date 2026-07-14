import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';

import { configureApiAuthInterceptors } from '@/auth/api-auth';
import { env } from '@/config/env';
import { supabase } from '@/lib/supabase';

type Credentials = {
  email: string;
  password: string;
};

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  isAuthInitializing: boolean;
  signIn: (credentials: Credentials) => Promise<void>;
  signUp: (credentials: Credentials) => Promise<void>;
  verifyOtp: (email: string, token: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

type AuthProviderProps = {
  children: ReactNode;
};

async function readSession(): Promise<Session | null> {
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw error;
  }

  return data.session;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isAuthInitializing, setIsAuthInitializing] = useState(true);

  useEffect(() => {
    configureApiAuthInterceptors({
      getAccessToken: async () => {
        const latestSession = await readSession();
        return latestSession?.access_token ?? null;
      },
      refreshAccessToken: async () => {
        const { data, error } = await supabase.auth.refreshSession();
        if (error) {
          return null;
        }

        return data.session?.access_token ?? null;
      },
    });

    let isMounted = true;

    void readSession()
      .then((initialSession) => {
        if (!isMounted) {
          return;
        }

        setSession(initialSession);
        setIsAuthInitializing(false);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        setSession(null);
        setIsAuthInitializing(false);
      });

    const { data: authSubscription } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(currentSession);
      if (isMounted) {
        setIsAuthInitializing(false);
      }
    });

    return () => {
      isMounted = false;
      authSubscription.subscription.unsubscribe();
    };
  }, []);

  const contextValue = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      session,
      isAuthInitializing,
      signIn: async ({ email, password }) => {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          throw error;
        }
      },
      signUp: async ({ email, password }) => {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) {
          throw error;
        }
      },
      verifyOtp: async (email: string, token: string) => {
        const { error } = await supabase.auth.verifyOtp({
          email,
          token,
          type: 'signup',
        });
        if (error) {
          throw error;
        }
      },
      resetPassword: async (email: string) => {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: env.passwordResetRedirectTo,
        });
        if (error) {
          throw error;
        }
      },
      logout: async () => {
        const { error } = await supabase.auth.signOut();
        if (error) {
          throw error;
        }
      },
      getAccessToken: async () => {
        const latestSession = await readSession();
        return latestSession?.access_token ?? null;
      },
    }),
    [isAuthInitializing, session],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const authContext = useContext(AuthContext);
  if (!authContext) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }

  return authContext;
}
