import { apiClient } from '@/lib/axios';

export type DocType = 'message' | 'formal_letter';
export type DocStatus = 'processing' | 'draft' | 'sent' | 'failed';

export type DocumentResponse = {
  id: string;
  property_id: string;
  deduction_notice_id: string | null;
  doc_type: DocType;
  status: DocStatus;
  ai_draft: string | null;
  edited_content: string | null;
  display_content: string | null;
  sent_at: string | null;
  created_at: string;
};

export type DocumentCreate = {
  property_id: string;
  deduction_notice_id: string;
  doc_type: DocType;
};

export type DocumentUpdate = {
  edited_content: string;
};

export const DocumentService = {
  getDocuments: async (propertyId: string): Promise<DocumentResponse[]> => {
    const response = await apiClient.get<DocumentResponse[]>('/generated-documents', {
      params: {
        property_id: propertyId,
      },
    });
    return response.data;
  },

  getDocument: async (id: string): Promise<DocumentResponse> => {
    const response = await apiClient.get<DocumentResponse>(`/generated-documents/${id}`);
    return response.data;
  },

  createDocument: async (data: DocumentCreate): Promise<DocumentResponse> => {
    const response = await apiClient.post<DocumentResponse>('/generated-documents', data);
    return response.data;
  },

  updateDocument: async (id: string, data: DocumentUpdate): Promise<DocumentResponse> => {
    const response = await apiClient.put<DocumentResponse>(`/generated-documents/${id}`, data);
    return response.data;
  },

  markDocumentSent: async (id: string): Promise<DocumentResponse> => {
    const response = await apiClient.post<DocumentResponse>(`/generated-documents/${id}/mark-sent`);
    return response.data;
  },
};
