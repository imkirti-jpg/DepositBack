import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LeaseService } from '@/services/lease.service';
import type { LeaseResponse } from '@/services/lease.service';

export function useLease(id: string) {
  return useQuery<LeaseResponse>({
    queryKey: ['lease', id],
    queryFn: () => LeaseService.getLease(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const lease = query.state.data;
      if (lease && lease.status === 'processing') {
        // Cap polling at 150 attempts (~300s) to prevent backend load if stuck
        if (query.state.dataUpdateCount > 150) {
          return false;
        }
        return 2000;
      }
      return false;
    },
  });
}

export function useUploadLease() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      propertyId,
      fileUri,
      fileName,
      fileType,
    }: {
      propertyId: string;
      fileUri: string;
      fileName: string;
      fileType: string;
    }) => LeaseService.uploadLease(propertyId, fileUri, fileName, fileType),
    onSuccess: (newLease) => {
      queryClient.setQueryData(['lease', newLease.id], newLease);
    },
  });
}

export function useReextractLease(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => LeaseService.reextractLease(id),
    onSuccess: (updatedLease) => {
      queryClient.setQueryData(['lease', id], updatedLease);
      queryClient.invalidateQueries({ queryKey: ['lease', id] });
    },
  });
}

export function useUpdateLease(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (extractedFields: Record<string, any>) =>
      LeaseService.updateLease(id, extractedFields),
    onSuccess: (updatedLease) => {
      queryClient.setQueryData(['lease', id], updatedLease);
      queryClient.invalidateQueries({ queryKey: ['lease', id] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', updatedLease.property_id] });
    },
  });
}
