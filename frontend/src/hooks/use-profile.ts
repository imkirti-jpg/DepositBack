import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ProfileService } from '@/services/profile.service';
import type {
  ProfileUpdate,
  PreferencesUpdate,
  ProfileResponse,
  PreferencesResponse,
} from '@/services/profile.service';

export function useProfile() {
  return useQuery<ProfileResponse>({
    queryKey: ['profile'],
    queryFn: () => ProfileService.getProfile(),
  });
}

export function usePreferences() {
  return useQuery<PreferencesResponse>({
    queryKey: ['preferences'],
    queryFn: () => ProfileService.getPreferences(),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProfileUpdate) => ProfileService.updateProfile(data),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(['profile'], updatedProfile);
    },
  });
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PreferencesUpdate) => ProfileService.updatePreferences(data),
    onSuccess: (updatedPrefs) => {
      queryClient.setQueryData(['preferences'], updatedPrefs);
    },
  });
}
