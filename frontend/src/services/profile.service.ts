import { apiClient } from '@/lib/axios';

export type ProfileResponse = {
  id: string;
  full_name: string | null;
  city: string | null;
  created_at: string;
};

export type ProfileUpdate = {
  full_name?: string;
  city?: string;
};

export type PreferencesResponse = {
  id: string;
  user_id: string;
  receive_email_notifications: boolean;
  receive_sms_notifications: boolean;
};

export type PreferencesUpdate = {
  receive_email_notifications?: boolean;
  receive_sms_notifications?: boolean;
};

export const ProfileService = {
  getProfile: async (): Promise<ProfileResponse> => {
    const response = await apiClient.get<ProfileResponse>('/me');
    return response.data;
  },

  updateProfile: async (data: ProfileUpdate): Promise<ProfileResponse> => {
    const response = await apiClient.put<ProfileResponse>('/me', data);
    return response.data;
  },

  getPreferences: async (): Promise<PreferencesResponse> => {
    const response = await apiClient.get<PreferencesResponse>('/preferences');
    return response.data;
  },

  updatePreferences: async (data: PreferencesUpdate): Promise<PreferencesResponse> => {
    const response = await apiClient.put<PreferencesResponse>('/preferences', data);
    return response.data;
  },
};
