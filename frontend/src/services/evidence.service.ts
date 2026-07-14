import { Platform } from 'react-native';
import { apiClient } from '@/lib/axios';

export type EvidencePhase = 'move_in' | 'move_out';

export type EvidenceResponse = {
  id: string;
  property_id: string;
  phase: EvidencePhase;
  room_label: string | null;
  file_url: string;
  notes: string | null;
  created_at: string;
};

export const EvidenceService = {
  uploadEvidence: async (
    propertyId: string,
    phase: EvidencePhase,
    fileUri: string,
    fileName: string,
    fileType: string,
    roomLabel?: string,
    notes?: string,
  ): Promise<EvidenceResponse> => {
    const formData = new FormData();
    formData.append('property_id', propertyId);
    formData.append('phase', phase);

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

    if (roomLabel) {
      formData.append('room_label', roomLabel);
    }
    if (notes) {
      formData.append('notes', notes);
    }

    const response = await apiClient.post<EvidenceResponse>('/evidence', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getEvidenceList: async (
    propertyId: string,
    phase?: EvidencePhase,
  ): Promise<EvidenceResponse[]> => {
    const params: Record<string, any> = { property_id: propertyId };
    if (phase) {
      params.phase = phase;
    }
    const response = await apiClient.get<EvidenceResponse[]>('/evidence', { params });
    return response.data;
  },

  deleteEvidence: async (id: string): Promise<void> => {
    await apiClient.delete(`/evidence/${id}`);
  },
};
