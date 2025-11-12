/**
 * React hooks for property data fetching
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, type PropertyFilters } from '@/lib/api-client';
import type { Property, ScoreResult } from '@/types';

/**
 * Fetch paginated properties
 */
export function useProperties(filters?: PropertyFilters) {
  return useQuery({
    queryKey: ['properties', filters],
    queryFn: () => apiClient.getProperties(filters),
    staleTime: 30000, // Consider data fresh for 30 seconds
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch single property by ID
 */
export function useProperty(id: string | undefined) {
  return useQuery({
    queryKey: ['property', id],
    queryFn: () => apiClient.getProperty(id!),
    enabled: !!id,
    staleTime: 30000,
  });
}

/**
 * Fetch property score
 */
export function usePropertyScore(propertyId: string | undefined) {
  return useQuery({
    queryKey: ['property-score', propertyId],
    queryFn: () => apiClient.getPropertyScore(propertyId!),
    enabled: !!propertyId,
    staleTime: 60000, // Scores don't change often
  });
}

/**
 * Invalidate property queries (used after mutations)
 */
export function useInvalidateProperty() {
  const queryClient = useQueryClient();

  return (propertyId: string) => {
    queryClient.invalidateQueries({ queryKey: ['property', propertyId] });
    queryClient.invalidateQueries({ queryKey: ['properties'] });
    queryClient.invalidateQueries({ queryKey: ['timeline', propertyId] });
  };
}
