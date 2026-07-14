import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Platform } from 'react-native';
import { apiClient } from '@/lib/axios';

export type EvidenceResponse = {
  id: string;
  property_id: string;
  phase: 'move_in' | 'move_out';
  room_label: string | null;
  file_url: string;
  file_hash: string | null;
  display_name: string;
  category: string;
  sort_order: number;
  notes: string | null;
  mime_type: string | null;
  file_size: number | null;
  width: number | null;
  height: number | null;
  captured_at: string | null;
  deleted_at: string | null;
  deleted_by: string | null;
  created_at: string;
  thumbnail_url: string | null;
  full_image_url: string | null;
};

export const EvidenceService = {
  getEvidenceList: async (propertyId: string, category?: string, includeDeleted = false): Promise<EvidenceResponse[]> => {
    const response = await apiClient.get<EvidenceResponse[]>('/evidence', {
      params: {
        property_id: propertyId,
        category,
        include_deleted: includeDeleted,
      },
    });
    return response.data;
  },

  uploadEvidence: async (
    propertyId: string,
    category: string,
    fileUris: string[],
    roomLabel?: string,
    notes?: string,
  ): Promise<EvidenceResponse[]> => {
    const formData = new FormData();
    formData.append('property_id', propertyId);
    formData.append('category', category);
    if (roomLabel) formData.append('room_label', roomLabel);
    if (notes) formData.append('notes', notes);

    for (let i = 0; i < fileUris.length; i++) {
      const uri = fileUris[i];
      const filename = uri.split('/').pop() || `evidence_${i}.jpg`;
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      if (Platform.OS === 'web') {
        const res = await fetch(uri);
        const blob = await res.blob();
        formData.append('files', blob, filename);
      } else {
        formData.append('files', {
          uri,
          name: filename,
          type,
        } as any);
      }
    }

    const response = await apiClient.post<EvidenceResponse[]>('/evidence', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  replaceEvidence: async (evidenceId: string, uri: string): Promise<EvidenceResponse> => {
    const formData = new FormData();
    const filename = uri.split('/').pop() || 'replaced_evidence.jpg';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1]}` : `image/jpeg`;

    if (Platform.OS === 'web') {
      const res = await fetch(uri);
      const blob = await res.blob();
      formData.append('file', blob, filename);
    } else {
      formData.append('file', {
        uri,
        name: filename,
        type,
      } as any);
    }

    const response = await apiClient.put<EvidenceResponse>(`/evidence/${evidenceId}/replace`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  deleteEvidence: async (evidenceId: string): Promise<void> => {
    await apiClient.delete(`/evidence/${evidenceId}`);
  },

  restoreEvidence: async (evidenceId: string): Promise<EvidenceResponse> => {
    const response = await apiClient.post<EvidenceResponse>(`/evidence/${evidenceId}/restore`);
    return response.data;
  },
};

export function useEvidenceList(propertyId: string, category?: string, includeDeleted = false) {
  return useQuery<EvidenceResponse[]>({
    queryKey: ['evidence-list', propertyId, category || 'all', includeDeleted],
    queryFn: () => EvidenceService.getEvidenceList(propertyId, category, includeDeleted),
    enabled: !!propertyId,
  });
}

export function useUploadEvidence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      propertyId,
      category,
      fileUris,
      roomLabel,
      notes,
    }: {
      propertyId: string;
      category: string;
      fileUris: string[];
      roomLabel?: string;
      notes?: string;
    }) => EvidenceService.uploadEvidence(propertyId, category, fileUris, roomLabel, notes),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['evidence-list', variables.propertyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', variables.propertyId] });
    },
  });
}

export function useReplaceEvidence(propertyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ evidenceId, uri }: { evidenceId: string; uri: string }) =>
      EvidenceService.replaceEvidence(evidenceId, uri),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-list', propertyId] });
    },
  });
}

export function useDeleteEvidence(propertyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (evidenceId: string) => EvidenceService.deleteEvidence(evidenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-list', propertyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', propertyId] });
    },
  });
}

export function useRestoreEvidence(propertyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (evidenceId: string) => EvidenceService.restoreEvidence(evidenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence-list', propertyId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', propertyId] });
    },
  });
}
