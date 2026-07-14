import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { PropertyService } from '@/services/property.service';
import type { PropertyUpdate, PropertyResponse } from '@/services/property.service';

const PROPERTIES_KEY = ['properties'];
const propertyKey = (id: string) => ['properties', id];

export function useProperties() {
  return useQuery<PropertyResponse[]>({
    queryKey: PROPERTIES_KEY,
    queryFn: PropertyService.getProperties,
  });
}

export function useProperty(id: string) {
  return useQuery<PropertyResponse>({
    queryKey: propertyKey(id),
    queryFn: () => PropertyService.getProperty(id),
    enabled: !!id,
  });
}

export function useCreateProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: PropertyService.createProperty,
    onSuccess: (newProperty) => {
      queryClient.setQueryData<PropertyResponse[]>(PROPERTIES_KEY, (old = []) => [
        ...old,
        newProperty,
      ]);
    },
  });
}

export function useUpdateProperty(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PropertyUpdate) => PropertyService.updateProperty(id, data),
    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey: PROPERTIES_KEY });
      await queryClient.cancelQueries({ queryKey: propertyKey(id) });

      const previousProperty = queryClient.getQueryData<PropertyResponse>(propertyKey(id));
      const previousProperties = queryClient.getQueryData<PropertyResponse[]>(PROPERTIES_KEY);

      if (previousProperty) {
        queryClient.setQueryData<PropertyResponse>(propertyKey(id), {
          ...previousProperty,
          ...newData,
        });
      }

      if (previousProperties) {
        queryClient.setQueryData<PropertyResponse[]>(
          PROPERTIES_KEY,
          previousProperties.map((p) => (p.id === id ? { ...p, ...newData } : p)),
        );
      }

      return { previousProperty, previousProperties };
    },
    onError: (err, newData, context) => {
      if (context?.previousProperty) {
        queryClient.setQueryData(propertyKey(id), context.previousProperty);
      }
      if (context?.previousProperties) {
        queryClient.setQueryData(PROPERTIES_KEY, context.previousProperties);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY });
      queryClient.invalidateQueries({ queryKey: propertyKey(id) });
      queryClient.invalidateQueries({ queryKey: ['dashboard', id] });
    },
  });
}

export function useDeleteProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => PropertyService.deleteProperty(id),
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<PropertyResponse[]>(PROPERTIES_KEY, (old = []) =>
        old.filter((p) => p.id !== deletedId),
      );
      queryClient.invalidateQueries({ queryKey: PROPERTIES_KEY });
    },
  });
}
