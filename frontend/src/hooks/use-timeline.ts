/**
 * React hooks for timeline data fetching and SSE subscriptions
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { apiClient, type CreateCommentRequest, type CreateNoteRequest, type UpdateNoteRequest } from '@/lib/api-client';
import type { TimelineEvent, TimelineStatistics } from '@/types';

/**
 * Fetch timeline events
 */
export function useTimeline(
  propertyId: string | undefined,
  options?: {
    limit?: number;
    event_types?: string[];
    include_system?: boolean;
  }
) {
  return useQuery({
    queryKey: ['timeline', propertyId, options],
    queryFn: () => apiClient.getTimeline(propertyId!, options),
    enabled: !!propertyId,
    staleTime: 10000, // Timeline changes frequently
  });
}

/**
 * Fetch timeline statistics
 */
export function useTimelineStatistics(propertyId: string | undefined) {
  return useQuery({
    queryKey: ['timeline-stats', propertyId],
    queryFn: () => apiClient.getTimelineStatistics(propertyId!),
    enabled: !!propertyId,
    staleTime: 30000,
  });
}

/**
 * Subscribe to timeline SSE stream for real-time updates
 */
export function useTimelineSubscription(propertyId: string | undefined) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!propertyId) return;

    let eventSource: EventSource | null = null;

    try {
      eventSource = apiClient.subscribeToTimeline(
        propertyId,
        (event: TimelineEvent) => {
          // Update query cache with new event
          queryClient.setQueryData<TimelineEvent[]>(['timeline', propertyId], (old = []) => {
            // Add new event to the beginning (newest first)
            return [event, ...old];
          });
        },
        (error) => {
          console.error('SSE connection error:', error);
          setError('Connection to real-time updates failed');
          setConnected(false);
        }
      );

      eventSource.addEventListener('open', () => {
        setConnected(true);
        setError(null);
      });

      return () => {
        eventSource?.close();
        setConnected(false);
      };
    } catch (err) {
      console.error('Failed to establish SSE connection:', err);
      setError('Failed to connect to real-time updates');
      return;
    }
  }, [propertyId, queryClient]);

  return { connected, error };
}

/**
 * Add comment mutation
 */
export function useAddComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateCommentRequest) => apiClient.addComment(request),
    onSuccess: (data, variables) => {
      // Optimistically add to cache
      queryClient.setQueryData<TimelineEvent[]>(['timeline', variables.property_id], (old = []) => [
        data,
        ...old,
      ]);
      // Invalidate to refetch
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.property_id] });
      queryClient.invalidateQueries({ queryKey: ['timeline-stats', variables.property_id] });
    },
  });
}

/**
 * Add note mutation
 */
export function useAddNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateNoteRequest) => apiClient.addNote(request),
    onSuccess: (data, variables) => {
      // Add event to timeline cache
      queryClient.setQueryData<TimelineEvent[]>(['timeline', variables.property_id], (old = []) => [
        data.event,
        ...old,
      ]);
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['timeline', variables.property_id] });
      queryClient.invalidateQueries({ queryKey: ['timeline-stats', variables.property_id] });
    },
  });
}

/**
 * Update note mutation
 */
export function useUpdateNote(propertyId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ noteId, data }: { noteId: string; data: UpdateNoteRequest }) =>
      apiClient.updateNote(noteId, data),
    onSuccess: () => {
      // Invalidate timeline to refetch
      queryClient.invalidateQueries({ queryKey: ['timeline', propertyId] });
    },
  });
}
