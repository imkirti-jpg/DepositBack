import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { DocumentService } from '@/services/document.service';
import type { DocumentCreate, DocumentUpdate, DocumentResponse } from '@/services/document.service';

export function useDocumentsList(propertyId: string) {
  return useQuery<DocumentResponse[]>({
    queryKey: ['documents', propertyId],
    queryFn: () => DocumentService.getDocuments(propertyId),
    enabled: !!propertyId,
  });
}

export function useDocument(id: string) {
  return useQuery<DocumentResponse>({
    queryKey: ['document', id],
    queryFn: () => DocumentService.getDocument(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const doc = query.state.data;
      if (doc && doc.status === 'processing') {
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

export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DocumentCreate) => DocumentService.createDocument(data),
    onSuccess: (newDoc) => {
      queryClient.setQueryData(['document', newDoc.id], newDoc);
      queryClient.invalidateQueries({ queryKey: ['documents', newDoc.property_id], exact: true });
      queryClient.invalidateQueries({ queryKey: ['dashboard', newDoc.property_id], exact: true });
    },
  });
}

export function useUpdateDocument(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DocumentUpdate) => DocumentService.updateDocument(id, data),
    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey: ['document', id] });
      const previousDoc = queryClient.getQueryData<DocumentResponse>(['document', id]);

      if (previousDoc) {
        queryClient.setQueryData<DocumentResponse>(['document', id], {
          ...previousDoc,
          edited_content: newData.edited_content,
          display_content: newData.edited_content,
        });
      }

      return { previousDoc };
    },
    onError: (err, newData, context) => {
      if (context?.previousDoc) {
        queryClient.setQueryData(['document', id], context.previousDoc);
      }
    },
    onSettled: (updatedDoc) => {
      queryClient.invalidateQueries({ queryKey: ['document', id], exact: true });
      if (updatedDoc) {
        queryClient.invalidateQueries({
          queryKey: ['documents', updatedDoc.property_id],
          exact: true,
        });
      }
    },
  });
}

export function useMarkDocumentSent(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => DocumentService.markDocumentSent(id),
    onSuccess: (updatedDoc) => {
      queryClient.setQueryData(['document', id], updatedDoc);
      queryClient.invalidateQueries({
        queryKey: ['documents', updatedDoc.property_id],
        exact: true,
      });
      queryClient.invalidateQueries({
        queryKey: ['dashboard', updatedDoc.property_id],
        exact: true,
      });
    },
  });
}
