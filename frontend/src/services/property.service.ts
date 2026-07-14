import { apiClient } from '@/lib/axios';

export type PropertyStatus = 'active' | 'resolved';

export type PropertyResponse = {
  id: string;
  user_id: string;
  label: string;
  address: string | null;
  deposit_amount: number;
  lease_start_date: string | null;
  lease_end_date: string | null;
  status: PropertyStatus;
  created_at: string;
  updated_at: string;
};

export type PropertyCreate = {
  label: string;
  address?: string;
  deposit_amount: number;
  lease_start_date?: string;
  lease_end_date?: string;
};

export type PropertyUpdate = Partial<PropertyCreate> & {
  status?: PropertyStatus;
};

export const PropertyService = {
  getProperties: async (): Promise<PropertyResponse[]> => {
    const response = await apiClient.get<PropertyResponse[]>('/properties');
    return response.data;
  },

  getProperty: async (id: string): Promise<PropertyResponse> => {
    const response = await apiClient.get<PropertyResponse>(`/properties/${id}`);
    return response.data;
  },

  createProperty: async (data: PropertyCreate): Promise<PropertyResponse> => {
    const payload = {
      ...data,
      address: data.address?.trim() || null,
      lease_start_date: data.lease_start_date?.trim() || null,
      lease_end_date: data.lease_end_date?.trim() || null,
    };
    const response = await apiClient.post<PropertyResponse>('/properties', payload);
    return response.data;
  },

  updateProperty: async (id: string, data: PropertyUpdate): Promise<PropertyResponse> => {
    const payload = {
      ...data,
      address: data.address === '' ? null : data.address,
      lease_start_date: data.lease_start_date === '' ? null : data.lease_start_date,
      lease_end_date: data.lease_end_date === '' ? null : data.lease_end_date,
    };
    const response = await apiClient.put<PropertyResponse>(`/properties/${id}`, payload);
    return response.data;
  },

  deleteProperty: async (id: string): Promise<void> => {
    await apiClient.delete(`/properties/${id}`);
  },
};
