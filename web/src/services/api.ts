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
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export default ApiClient;
