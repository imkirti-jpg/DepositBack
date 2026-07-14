import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ClaimService } from '@/services/claim.service';
import type { NoticeResponse, ClaimResponse, ClaimUpdate } from '@/services/claim.service';

export function useNotice(id: string) {
  return useQuery<NoticeResponse>({
    queryKey: ['notice', id],
    queryFn: () => ClaimService.getNotice(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const notice = query.state.data;
      if (notice && notice.status === 'processing') {
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

export function useNoticeClaims(noticeId: string) {
  return useQuery<ClaimResponse[]>({
    queryKey: ['claims', noticeId],
    queryFn: () => ClaimService.getNoticeClaims(noticeId),
    enabled: !!noticeId,
  });
}

export function useUploadNotice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      propertyId,
      fileUri,
      fileName,
      fileType,
      rawText,
    }: {
      propertyId: string;
      fileUri?: string;
      fileName?: string;
      fileType?: string;
      rawText?: string;
    }) => ClaimService.uploadNotice(propertyId, fileUri, fileName, fileType, rawText),
    onSuccess: (newNotice) => {
      queryClient.setQueryData(['notice', newNotice.id], newNotice);
      queryClient.invalidateQueries({
        queryKey: ['dashboard', newNotice.property_id],
        exact: true,
      });
    },
  });
}

export function useUpdateClaim(propertyId: string, noticeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ claimId, data }: { claimId: string; data: ClaimUpdate }) =>
      ClaimService.updateClaim(claimId, data),
    onMutate: async ({ claimId, data }) => {
      await queryClient.cancelQueries({ queryKey: ['claims', noticeId] });

      const previousClaims = queryClient.getQueryData<ClaimResponse[]>(['claims', noticeId]);

      if (previousClaims) {
        queryClient.setQueryData<ClaimResponse[]>(
          ['claims', noticeId],
          previousClaims.map((c) => (c.id === claimId ? { ...c, ...data } : c)),
        );
      }

      return { previousClaims };
    },
    onError: (err, variables, context) => {
      if (context?.previousClaims) {
        queryClient.setQueryData(['claims', noticeId], context.previousClaims);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['claims', noticeId], exact: true });
      queryClient.invalidateQueries({ queryKey: ['dashboard', propertyId], exact: true });
    },
  });
}
