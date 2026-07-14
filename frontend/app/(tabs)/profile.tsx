import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { ScrollView, Text, View, Switch } from 'react-native';
import { z } from 'zod';

import { useAuth } from '@/auth/auth-context';
import { Card } from '@/components/ui/card';
import { ErrorState } from '@/components/ui/error-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import {
  useProfile,
  usePreferences,
  useUpdateProfile,
  useUpdatePreferences,
} from '@/hooks/use-profile';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const profileFormSchema = z.object({
  full_name: z.string().min(1, 'Full name is required.'),
  city: z.string().min(1, 'City is required.'),
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

export default function ProfileScreen() {
  const { logout, user: authUser } = useAuth();

  // Queries
  const {
    data: profile,
    isLoading: isProfileLoading,
    error: profileError,
    refetch: refetchProfile,
  } = useProfile();
  const {
    data: preferences,
    isLoading: isPrefsLoading,
    error: prefsError,
    refetch: refetchPrefs,
  } = usePreferences();

  // Mutations
  const updateProfileMutation = useUpdateProfile();
  const updatePrefsMutation = useUpdatePreferences();

  // Edit states
  const [isEditing, setIsEditing] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    values: profile
      ? {
          full_name: profile.full_name || '',
          city: profile.city || '',
        }
      : undefined,
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await updateProfileMutation.mutateAsync({
        full_name: values.full_name,
        city: values.city,
      });
      setIsEditing(false);
    } catch {
      // Handled by API layer
    }
  });

  const handleTogglePreference = async (type: 'email' | 'sms', value: boolean) => {
    try {
      if (type === 'email') {
        await updatePrefsMutation.mutateAsync({
          receive_email_notifications: value,
        });
      } else {
        await updatePrefsMutation.mutateAsync({
          receive_sms_notifications: value,
        });
      }
    } catch {
      // Handled by API layer
    }
  };

  const handleRetry = () => {
    void refetchProfile();
    void refetchPrefs();
  };

  if (isProfileLoading || isPrefsLoading) {
    return <LoadingSpinner fullscreen message="Retrieving account info..." />;
  }

  if (profileError || prefsError || !profile || !preferences) {
    return (
      <View className="flex-1 justify-center bg-slate-50 px-6">
        <ErrorState
          title="Profile Error"
          message="Could not load profile or notification preferences."
          onRetry={handleRetry}
        />
      </View>
    );
  }

  return (
    <View className="flex-1 bg-slate-50 px-6 pb-6 pt-12">
      <View className="mb-6 flex-row items-center justify-between">
        <View>
          <Text className="text-xs font-semibold uppercase tracking-wider text-brand-500">
            Account Management
          </Text>
          <Text className="text-3xl font-bold text-slate-900">Your Profile</Text>
        </View>
      </View>

      <ScrollView className="flex-1 gap-6" showsVerticalScrollIndicator={false}>
        {/* Account Metadata Card */}
        <Card title="Account Information" subtitle="System authentication credentials.">
          <View className="gap-4">
            <View>
              <Text className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Email Address
              </Text>
              <Text className="mt-0.5 text-sm font-semibold text-slate-700">{authUser?.email}</Text>
            </View>

            <View>
              <Text className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Profile Created
              </Text>
              <Text className="mt-0.5 text-sm text-slate-600 font-mono">
                {new Date(profile.created_at).toLocaleDateString()}
              </Text>
            </View>
          </View>
        </Card>

        {/* Profile Settings Card */}
        <Card title="Profile Details" subtitle="Manage your personal details.">
          {isEditing ? (
            <View className="gap-4">
              <Controller
                control={control}
                name="full_name"
                render={({ field: { onChange, value } }) => (
                  <Input
                    label="Full Name"
                    placeholder="Enter your full name"
                    value={value}
                    onChangeText={onChange}
                    errorMessage={errors.full_name?.message}
                  />
                )}
              />

              <Controller
                control={control}
                name="city"
                render={({ field: { onChange, value } }) => (
                  <Input
                    label="City / Location"
                    placeholder="Enter your current city"
                    value={value}
                    onChangeText={onChange}
                    errorMessage={errors.city?.message}
                  />
                )}
              />

              <View className="flex-row gap-2 mt-2">
                <View className="flex-1">
                  <Button
                    label="Save Changes"
                    loading={updateProfileMutation.isPending}
                    onPress={() => void onSubmit()}
                  />
                </View>
                <View className="flex-1">
                  <Button label="Cancel" variant="outline" onPress={() => setIsEditing(false)} />
                </View>
              </View>
            </View>
          ) : (
            <View className="gap-4">
              <View>
                <Text className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Full Name
                </Text>
                <Text className="mt-0.5 text-base font-bold text-slate-800">
                  {profile.full_name || 'Not provided'}
                </Text>
              </View>

              <View>
                <Text className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  City Location
                </Text>
                <Text className="mt-0.5 text-base font-medium text-slate-800">
                  {profile.city || 'Not provided'}
                </Text>
              </View>

              <Button
                label="Edit Profile"
                variant="outline"
                className="mt-2"
                onPress={() => setIsEditing(true)}
              />
            </View>
          )}
        </Card>

        {/* Notification Preferences Card */}
        <Card title="Dispute Notifications" subtitle="Keep track of extraction status & verdicts.">
          <View className="gap-4">
            <View className="flex-row items-center justify-between border-b border-slate-100 pb-3">
              <View className="flex-1 mr-4">
                <Text className="text-sm font-semibold text-slate-800">Email Alerts</Text>
                <Text className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                  Receive notifications when dispute documents or extractions complete.
                </Text>
              </View>
              <Switch
                value={preferences.receive_email_notifications}
                onValueChange={(val) => void handleTogglePreference('email', val)}
                trackColor={{ true: '#0f6cbd', false: '#cbd5e1' }}
              />
            </View>

            <View className="flex-row items-center justify-between">
              <View className="flex-1 mr-4">
                <Text className="text-sm font-semibold text-slate-800">SMS Notifications</Text>
                <Text className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                  Receive text messages when verdict recommendations change.
                </Text>
              </View>
              <Switch
                value={preferences.receive_sms_notifications}
                onValueChange={(val) => void handleTogglePreference('sms', val)}
                trackColor={{ true: '#0f6cbd', false: '#cbd5e1' }}
              />
            </View>
          </View>
        </Card>

        {/* Session Action Card */}
        <Card title="Sign Out">
          <Button label="Logout" variant="danger" onPress={() => void logout()} />
        </Card>
      </ScrollView>
    </View>
  );
}
