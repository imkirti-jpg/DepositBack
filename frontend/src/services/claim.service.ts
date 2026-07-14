import { Platform } from 'react-native';
import { apiClient } from '@/lib/axios';

export type NoticeStatus = 'processing' | 'completed' | 'failed';

export type NoticeResponse = {
  id: string;
  property_id: string;
  file_url: string | null;
  raw_text: string | null;
  status: NoticeStatus;
  created_at: string;
};

export type ClaimLabel = 'supported' | 'weak' | 'unsupported' | 'unclear';

export type ClaimResponse = {
  id: string;
  deduction_notice_id: string;
  item_description: string;
  claimed_amount: number | null;
  label: ClaimLabel;
  reasoning: string;
  evidence_refs: Record<string, string>;
  user_override_label: ClaimLabel | null;
  effective_label: ClaimLabel | null;
};

export type ClaimUpdate = {
  user_override_label?: ClaimLabel;
};

export const ClaimService = {
  uploadNotice: async (
    propertyId: string,
    fileUri?: string,
    fileName?: string,
    fileType?: string,
    rawText?: string,
  ): Promise<NoticeResponse> => {
    const formData = new FormData();
    formData.append('property_id', propertyId);

    if (fileUri && fileName && fileType) {
      if (Platform.OS === 'web') {
        const res = await fetch(fileUri);
        const blob = await res.blob();
        formData.append('file', blob, fileName);
      } else {
        // React Native FormData requires a custom object with uri, name, and type properties
        // We cast it to any because the TypeScript standard lib's FormData.append only expects Blob | string.
        formData.append('file', {
          uri: fileUri,
          name: fileName,
          type: fileType,
        } as any);
      }
    }

    if (rawText) {
      formData.append('raw_text', rawText);
    }

    const response = await apiClient.post<NoticeResponse>('/deduction-notices', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getNotice: async (id: string): Promise<NoticeResponse> => {
    const response = await apiClient.get<NoticeResponse>(`/deduction-notices/${id}`);
    return response.data;
  },

  getNoticeClaims: async (noticeId: string): Promise<ClaimResponse[]> => {
    const response = await apiClient.get<ClaimResponse[]>(`/deduction-notices/${noticeId}/claims`);
    return response.data;
  },

  updateClaim: async (id: string, data: ClaimUpdate): Promise<ClaimResponse> => {
    const response = await apiClient.put<ClaimResponse>(`/claims/${id}`, data);
    return response.data;
  },
};
