/**
 * React Query hooks for property data
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import type {
  PropertyDetail,
  ProvenanceStatsResponse,
  FieldHistoryResponse,
  ScoreExplainabilityDetail,
} from '@/types/provenance';

/**
 * Fetch property details with provenance
 */
export function useProperty(propertyId: string): UseQueryResult<PropertyDetail> {
  return useQuery({
    queryKey: ['property', propertyId],
    queryFn: () => apiClient.getProperty(propertyId),
    enabled: !!propertyId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Fetch provenance statistics
 */
export function useProvenanceStats(propertyId: string): UseQueryResult<ProvenanceStatsResponse> {
  return useQuery({
    queryKey: ['provenance-stats', propertyId],
    queryFn: () => apiClient.getProvenanceStats(propertyId),
    enabled: !!propertyId,
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * Fetch field history
 */
export function useFieldHistory(
  propertyId: string,
  fieldPath: string,
  enabled: boolean = false
): UseQueryResult<FieldHistoryResponse> {
  return useQuery({
    queryKey: ['field-history', propertyId, fieldPath],
    queryFn: () => apiClient.getFieldHistory(propertyId, fieldPath),
    enabled: enabled && !!propertyId && !!fieldPath,
    staleTime: 1000 * 60 * 10, // 10 minutes - history doesn't change frequently
  });
}

/**
 * Fetch scorecard with explainability
 */
export function useScorecard(propertyId: string): UseQueryResult<ScoreExplainabilityDetail> {
  return useQuery({
    queryKey: ['scorecard', propertyId],
    queryFn: () => apiClient.getScorecard(propertyId),
    enabled: !!propertyId,
    staleTime: 1000 * 60 * 5,
  });
}
