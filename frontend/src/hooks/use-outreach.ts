/**
 * React hooks for outreach campaign data
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

/**
 * Fetch outreach campaigns for a property
 */
export function useOutreachCampaigns(propertyId: string | undefined) {
  return useQuery({
    queryKey: ['outreach', propertyId],
    queryFn: () => apiClient.getOutreachCampaigns(propertyId!),
    enabled: !!propertyId,
    staleTime: 30000,
  });
}
