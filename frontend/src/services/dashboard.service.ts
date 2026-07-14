import { apiClient } from '@/lib/axios';

export type ClaimSummary = {
  id: string;
  item_description: string;
  claimed_amount: number | null;
  effective_label: 'supported' | 'weak' | 'unsupported' | 'unclear';
};

export type DocumentSummary = {
  id: string;
  doc_type: 'message' | 'formal_letter';
  status: 'processing' | 'draft' | 'sent' | 'failed';
  sent_at: string | null;
};

export type DashboardResponse = {
  property_id: string;
  property_label: string;
  property_status: 'active' | 'resolved';
  deposit_amount: number;
  lease_id: string | null;
  lease_status: 'processing' | 'needs_review' | 'confirmed' | 'failed' | null;
  move_in_evidence_count: number;
  move_out_evidence_count: number;
  notice_id: string | null;
  notice_status: string | null;
  claims: ClaimSummary[];
  total_supported_amount: number;
  total_disputed_amount: number;
  total_unquantified_count: number;
  documents: DocumentSummary[];
  next_action: string;
};

export const DashboardService = {
  getDashboard: async (propertyId: string): Promise<DashboardResponse> => {
    const response = await apiClient.get<DashboardResponse>(`/properties/${propertyId}/dashboard`);
    return response.data;
  },
};
