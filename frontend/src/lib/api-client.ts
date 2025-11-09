/**
 * API Client for Real Estate OS Backend
 *
 * Provides type-safe methods for interacting with the FastAPI backend.
 * Includes support for SSE (Server-Sent Events) for real-time updates.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  Property,
  PropertyState,
  TimelineEvent,
  TimelineNote,
  TimelineStatistics,
  OutreachCampaign,
  ScoreResult,
} from '@/types';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface PropertyFilters {
  state?: PropertyState[];
  county?: string;
  zip?: string;
  min_score?: number;
  max_score?: number;
  search?: string;
  page?: number;
  per_page?: number;
}

export interface CreateCommentRequest {
  property_id: string;
  content: string;
  attachments?: string[];
}

export interface CreateNoteRequest {
  property_id: string;
  title: string;
  content: string;
  is_private?: boolean;
  attachments?: string[];
}

export interface UpdateNoteRequest {
  title?: string;
  content?: string;
}

export interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

/**
 * API Client class
 */
export class ApiClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.client = axios.create({
      baseURL: `${this.baseURL}/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor (for auth tokens in PR12)
    this.client.interceptors.request.use(
      (config) => {
        // TODO: Add JWT token from auth context
        // const token = getAuthToken();
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`;
        // }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const apiError: ApiError = {
          message: error.message,
          status: error.response?.status || 500,
          details: error.response?.data,
        };
        return Promise.reject(apiError);
      }
    );
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/healthz');
    return response.data;
  }

  /**
   * Database ping
   */
  async ping(): Promise<{ status: string; database: string }> {
    const response = await this.client.get('/ping');
    return response.data;
  }

  /**
   * Get properties with filters and pagination
   */
  async getProperties(filters?: PropertyFilters): Promise<PaginatedResponse<Property>> {
    const response = await this.client.get('/properties', {
      params: filters,
    });
    return response.data;
  }

  /**
   * Get property by ID
   */
  async getProperty(id: string): Promise<Property> {
    const response = await this.client.get(`/properties/${id}`);
    return response.data;
  }

  /**
   * Get property score
   */
  async getPropertyScore(propertyId: string): Promise<ScoreResult> {
    const response = await this.client.get(`/properties/${propertyId}/score`);
    return response.data;
  }

  /**
   * Get property timeline events
   */
  async getTimeline(
    propertyId: string,
    options?: {
      limit?: number;
      offset?: number;
      event_types?: string[];
      include_system?: boolean;
    }
  ): Promise<TimelineEvent[]> {
    const response = await this.client.get(`/properties/${propertyId}/timeline`, {
      params: options,
    });
    return response.data;
  }

  /**
   * Get timeline statistics
   */
  async getTimelineStatistics(propertyId: string): Promise<TimelineStatistics> {
    const response = await this.client.get(`/properties/${propertyId}/timeline/statistics`);
    return response.data;
  }

  /**
   * Add comment to property
   */
  async addComment(request: CreateCommentRequest): Promise<TimelineEvent> {
    const response = await this.client.post(`/properties/${request.property_id}/comments`, request);
    return response.data;
  }

  /**
   * Add note to property
   */
  async addNote(request: CreateNoteRequest): Promise<{ note_id: string; event: TimelineEvent }> {
    const response = await this.client.post(`/properties/${request.property_id}/notes`, request);
    return response.data;
  }

  /**
   * Update note
   */
  async updateNote(noteId: string, request: UpdateNoteRequest): Promise<TimelineNote> {
    const response = await this.client.patch(`/notes/${noteId}`, request);
    return response.data;
  }

  /**
   * Get outreach campaigns for property
   */
  async getOutreachCampaigns(propertyId: string): Promise<OutreachCampaign[]> {
    const response = await this.client.get(`/properties/${propertyId}/outreach`);
    return response.data;
  }

  /**
   * Subscribe to property timeline SSE stream
   *
   * Returns an EventSource that emits timeline events in real-time.
   * Call .close() on the returned EventSource to unsubscribe.
   */
  subscribeToTimeline(
    propertyId: string,
    onEvent: (event: TimelineEvent) => void,
    onError?: (error: Event) => void
  ): EventSource {
    const url = `${this.baseURL}/v1/properties/${propertyId}/timeline/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('timeline-event', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as TimelineEvent;
        onEvent(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    });

    if (onError) {
      eventSource.onerror = onError;
    }

    return eventSource;
  }

  /**
   * Subscribe to property state changes SSE stream
   */
  subscribeToState(
    propertyId: string,
    onStateChange: (state: PropertyState) => void,
    onError?: (error: Event) => void
  ): EventSource {
    const url = `${this.baseURL}/v1/properties/${propertyId}/state/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('state-change', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        onStateChange(data.new_state as PropertyState);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    });

    if (onError) {
      eventSource.onerror = onError;
    }

    return eventSource;
  }
}

// Singleton instance
export const apiClient = new ApiClient();
