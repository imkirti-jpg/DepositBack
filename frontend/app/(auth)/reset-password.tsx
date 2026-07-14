import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'expo-router';
import { Controller, useForm } from 'react-hook-form';
import { Text } from 'react-native';
import { useState } from 'react';

import { useAuth } from '@/auth/auth-context';
import { type ResetPasswordFormValues, resetPasswordSchema } from '@/auth/schemas';
import { AuthShell } from '@/components/auth/auth-shell';
import { AppButton } from '@/components/ui/app-button';
import { AppInput } from '@/components/ui/app-input';
import { InlineMessage } from '@/components/ui/inline-message';

export default function ResetPasswordScreen() {
  const { resetPassword } = useAuth();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      email: '',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await resetPassword(values.email);
      setSuccessMessage('Password reset email sent. Check your inbox.');
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Password reset failed. Please try again.',
      );
    }
  });

  return (
    <AuthShell title="Reset password" subtitle="We will send a password reset link to your email.">
      {errorMessage ? <InlineMessage type="error" message={errorMessage} /> : null}
      {successMessage ? <InlineMessage type="success" message={successMessage} /> : null}

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

      <AppButton label="Send reset link" loading={isSubmitting} onPress={() => void onSubmit()} />

      <Text className="mt-4 text-sm text-slate-600">
        Return to{' '}
        <Link href="/(auth)/login" className="font-semibold text-brand-700">
          Login
        </Link>
      </Text>
    </AuthShell>
  );
}
