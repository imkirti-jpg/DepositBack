import { zodResolver } from '@hookform/resolvers/zod';
import { Link, router } from 'expo-router';
import { Controller, useForm } from 'react-hook-form';
import { Text } from 'react-native';
import { useState } from 'react';

import { useAuth } from '@/auth/auth-context';
import { type LoginFormValues, loginSchema } from '@/auth/schemas';
import { AuthShell } from '@/components/auth/auth-shell';
import { AppButton } from '@/components/ui/app-button';
import { AppInput } from '@/components/ui/app-input';
import { InlineMessage } from '@/components/ui/inline-message';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setErrorMessage(null);
    try {
      await signIn(values);
      router.replace('/(tabs)/home');
    } catch (error) {
      let msg = error instanceof Error ? error.message : 'Login failed. Please try again.';
      if (
        msg.toLowerCase().includes('email not confirmed') ||
        msg.toLowerCase().includes('email not verified')
      ) {
        msg +=
          '\n\n💡 Dev Tip: Confirm the email in your inbox, or open your Supabase Console -> Auth -> Providers -> Email and toggle off "Confirm email" to disable verification requirements.';
      }
      setErrorMessage(msg);
    }
  });

  return (
    <AuthShell title="Login" subtitle="Access your DepositBack account.">
      {errorMessage ? <InlineMessage type="error" message={errorMessage} /> : null}

      <Controller
        control={control}
        name="email"
        render={({ field: { onChange, onBlur, value } }) => (
          <AppInput
            label="Email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            onBlur={onBlur}
            onChangeText={onChange}
            value={value}
            placeholder="you@example.com"
            errorMessage={errors.email?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="password"
        render={({ field: { onChange, onBlur, value } }) => (
          <AppInput
            label="Password"
            secureTextEntry
            autoCapitalize="none"
            autoComplete="password"
            onBlur={onBlur}
            onChangeText={onChange}
            value={value}
            placeholder="Enter your password"
            errorMessage={errors.password?.message}
          />
        )}
      />

      <AppButton label="Login" loading={isSubmitting} onPress={() => void onSubmit()} />

      <Text className="mt-4 text-sm text-slate-600">
        New user?{' '}
        <Link href="/(auth)/signup" className="font-semibold text-brand-700">
          Create account
        </Link>
      </Text>

      <Text className="mt-2 text-sm text-slate-600">
        Forgot your password?{' '}
        <Link href="/(auth)/reset-password" className="font-semibold text-brand-700">
          Reset it
        </Link>
      </Text>
    </AuthShell>
  );
}
