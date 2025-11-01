/**
 * API Client for Real Estate OS Backend
 * Handles all HTTP requests to FastAPI endpoints
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  PropertyDetail,
  ProvenanceStatsResponse,
  FieldHistoryResponse,
  ScoreExplainabilityDetail,
  SimilarPropertiesResponse,
  RecommendationsResponse,
  FeedbackResponse,
} from '@/types/provenance';

class ApiClient {
  private client: AxiosInstance;
  private tenantId: string;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Default tenant ID - in production, this would come from auth context
    this.tenantId = import.meta.env.VITE_TENANT_ID || '00000000-0000-0000-0000-000000000001';

    // Request interceptor to add tenant_id to all requests
    this.client.interceptors.request.use(
      (config) => {
        config.params = {
          ...config.params,
          tenant_id: this.tenantId,
        };
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          // Server responded with error status
          console.error('API Error:', error.response.status, error.response.data);
        } else if (error.request) {
          // Request made but no response received
          console.error('Network Error:', error.message);
        } else {
          // Something else happened
          console.error('Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  /**
   * Get property details with provenance
   */
  async getProperty(propertyId: string): Promise<PropertyDetail> {
    const response = await this.client.get<PropertyDetail>(`/properties/${propertyId}`);
    return response.data;
  }

  /**
   * Get provenance statistics for a property
   */
  async getProvenanceStats(propertyId: string): Promise<ProvenanceStatsResponse> {
    const response = await this.client.get<ProvenanceStatsResponse>(
      `/properties/${propertyId}/provenance`
    );
    return response.data;
  }

  /**
   * Get field history for a specific field
   */
  async getFieldHistory(
    propertyId: string,
    fieldPath: string,
    limit?: number
  ): Promise<FieldHistoryResponse> {
    const response = await this.client.get<FieldHistoryResponse>(
      `/properties/${propertyId}/history/${fieldPath}`,
      {
        params: { limit },
      }
    );
    return response.data;
  }

  /**
   * Get latest scorecard with explainability
   */
  async getScorecard(propertyId: string): Promise<ScoreExplainabilityDetail> {
    const response = await this.client.get<ScoreExplainabilityDetail>(
      `/properties/${propertyId}/scorecard`
    );
    return response.data;
  }

  // =====================================================================
  // WAVE 2.3/2.4: ML-Powered Similarity Search & Feedback
  // =====================================================================

  /**
   * Get similar properties using ML embeddings (Wave 2.3)
   */
  async getSimilarProperties(
    propertyId: string,
    options?: {
      top_k?: number;
      property_type?: string;
      zipcode?: string;
    }
  ): Promise<SimilarPropertiesResponse> {
    const response = await this.client.get<SimilarPropertiesResponse>(
      `/properties/${propertyId}/similar`,
      {
        params: options,
      }
    );
    return response.data;
  }

  /**
   * Get personalized recommendations for user (Wave 2.3)
   */
  async getRecommendations(
    userId: number,
    options?: {
      top_k?: number;
      filters?: Record<string, any>;
    }
  ): Promise<RecommendationsResponse> {
    const response = await this.client.post<RecommendationsResponse>(
      '/properties/recommend',
      {
        user_id: userId,
        top_k: options?.top_k || 10,
        filters: options?.filters,
      }
    );
    return response.data;
  }

  /**
   * Submit user feedback (like/dislike) for a property (Wave 2.3)
   */
  async submitFeedback(
    propertyId: string,
    userId: number,
    feedback: 'like' | 'dislike'
  ): Promise<FeedbackResponse> {
    const response = await this.client.post<FeedbackResponse>(
      `/properties/${propertyId}/feedback`,
      {
        user_id: userId,
        feedback: feedback,
      }
    );
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export default ApiClient;
