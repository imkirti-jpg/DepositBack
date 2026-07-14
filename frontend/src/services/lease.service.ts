import { Platform } from 'react-native';
import { apiClient } from '@/lib/axios';

export type LeaseStatus = 'processing' | 'needs_review' | 'confirmed' | 'failed';

export type LeaseResponse = {
  id: string;
  property_id: string;
  file_url: string;
  extracted_fields: Record<string, any> | null;
  status: LeaseStatus;
  created_at: string;
  updated_at: string;
};

export const LeaseService = {
  uploadLease: async (
    propertyId: string,
    fileUri: string,
    fileName: string,
    fileType: string,
  ): Promise<LeaseResponse> => {
    const formData = new FormData();
    formData.append('property_id', propertyId);

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

    const response = await apiClient.post<LeaseResponse>('/lease', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getLease: async (id: string): Promise<LeaseResponse> => {
    const response = await apiClient.get<LeaseResponse>(`/lease/${id}`);
    return response.data;
  },

  updateLease: async (id: string, extractedFields: Record<string, any>): Promise<LeaseResponse> => {
    const response = await apiClient.put<LeaseResponse>(`/lease/${id}`, {
      extracted_fields: extractedFields,
    });
    return response.data;
  },

  reextractLease: async (id: string): Promise<LeaseResponse> => {
    const response = await apiClient.post<LeaseResponse>(`/lease/${id}/reextract`);
    return response.data;
  },
};
