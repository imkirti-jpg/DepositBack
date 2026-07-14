import { useQuery } from '@tanstack/react-query';
import { DashboardService } from '@/services/dashboard.service';
import type { DashboardResponse } from '@/services/dashboard.service';

export function useDashboard(propertyId: string) {
  return useQuery<DashboardResponse>({
    queryKey: ['dashboard', propertyId],
    queryFn: () => DashboardService.getDashboard(propertyId),
    enabled: !!propertyId,
  });
}
