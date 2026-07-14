import { zodResolver } from '@hookform/resolvers/zod';
import { Link, router } from 'expo-router';
import { Controller, useForm } from 'react-hook-form';
import { Text, Alert, View } from 'react-native';
import { useState } from 'react';

import { useAuth } from '@/auth/auth-context';
import { type SignupFormValues, signupSchema } from '@/auth/schemas';
import { AuthShell } from '@/components/auth/auth-shell';
import { AppButton } from '@/components/ui/app-button';
import { AppInput } from '@/components/ui/app-input';
import { InlineMessage } from '@/components/ui/inline-message';

export default function SignupScreen() {
  const { signUp, verifyOtp } = useAuth();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isOtpStage, setIsOtpStage] = useState(false);
  const [emailForOtp, setEmailForOtp] = useState('');
  const [otpToken, setOtpToken] = useState('');
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await signUp({ email: values.email, password: values.password });
      setEmailForOtp(values.email);
      setSuccessMessage(
        'Registration successful. We sent a 6-digit verification code (OTP) to your email.',
      );
      setIsOtpStage(true);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Signup failed. Please try again.');
    }
  });

  const handleVerifyOtp = async () => {
    if (!otpToken.trim()) {
      setErrorMessage('Please enter the verification code.');
      return;
    }
    setErrorMessage(null);
    setIsVerifyingOtp(true);
    try {
      await verifyOtp(emailForOtp, otpToken.trim());
      Alert.alert(
        'Account Verified',
        'Your email has been successfully verified! You can now log in to your account.',
        [{ text: 'Proceed to Login', onPress: () => router.replace('/(auth)/login') }],
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Verification failed. Please check the code.',
      );
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  if (isOtpStage) {
    return (
      <AuthShell
        title="Verify email"
        subtitle={`Enter the 6-digit OTP code sent to ${emailForOtp}`}
      >
        {errorMessage ? <InlineMessage type="error" message={errorMessage} /> : null}
        {successMessage ? <InlineMessage type="success" message={successMessage} /> : null}

        <View className="mb-4">
          <AppInput
            label="Verification Code (OTP)"
            value={otpToken}
            onChangeText={setOtpToken}
            placeholder="Enter 6-digit code"
            keyboardType="number-pad"
            maxLength={6}
          />
        </View>

        <AppButton
          label="Verify Account"
          loading={isVerifyingOtp}
          onPress={() => void handleVerifyOtp()}
        />

        <Text
          className="mt-6 text-sm text-brand-700 font-semibold text-center"
          onPress={() => {
            setIsOtpStage(false);
            setErrorMessage(null);
            setSuccessMessage(null);
            setOtpToken('');
            reset();
          }}
        >
          Back to Signup
        </Text>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Create account" subtitle="Start recovering your deposit with confidence.">
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
            placeholder="Create a password"
            errorMessage={errors.password?.message}
          />
        )}
      />

      <Controller
        control={control}
        name="confirmPassword"
        render={({ field: { onChange, onBlur, value } }) => (
          <AppInput
            label="Confirm password"
            secureTextEntry
            autoCapitalize="none"
            autoComplete="password"
            onBlur={onBlur}
            onChangeText={onChange}
            value={value}
            placeholder="Confirm your password"
            errorMessage={errors.confirmPassword?.message}
          />
        )}
      />

      <AppButton label="Create account" loading={isSubmitting} onPress={() => void onSubmit()} />

      <Text className="mt-4 text-sm text-slate-600">
        Already have an account?{' '}
        <Link href="/(auth)/login" className="font-semibold text-brand-700">
          Login
        </Link>
      </Text>
    </AuthShell>
  );
}
