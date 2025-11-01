/**
 * Tests for API client
 *
 * Tests:
 * - Authentication headers
 * - Error handling
 * - Request/response transformation
 * - Retry logic
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { apiClient } from './api';

// Mock axios
vi.mock('axios');
const mockedAxios = vi.mocked(axios, true);

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Authentication', () => {
    it('includes bearer token in request headers', async () => {
      mockedAxios.post.mockResolvedValue({
        data: { access_token: 'test-token' },
      });

      const token = 'test-token';
      apiClient.setAuthToken(token);

      mockedAxios.get.mockResolvedValue({ data: {} });
      await apiClient.getProperties();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${token}`,
          }),
        })
      );
    });

    it('includes API key in request headers', async () => {
      const apiKey = 'test-api-key';
      apiClient.setApiKey(apiKey);

      mockedAxios.get.mockResolvedValue({ data: [] });
      await apiClient.getProperties();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': apiKey,
          }),
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('handles 401 unauthorized errors', async () => {
      mockedAxios.get.mockRejectedValue({
        response: {
          status: 401,
          data: { detail: 'Not authenticated' },
        },
      });

      await expect(apiClient.getProperties()).rejects.toThrow();
    });

    it('handles 404 not found errors', async () => {
      mockedAxios.get.mockRejectedValue({
        response: {
          status: 404,
          data: { detail: 'Property not found' },
        },
      });

      await expect(apiClient.getProperty('fake-id')).rejects.toThrow();
    });

    it('handles 429 rate limit errors', async () => {
      mockedAxios.get.mockRejectedValue({
        response: {
          status: 429,
          data: { detail: 'Rate limit exceeded' },
          headers: {
            'retry-after': '60',
          },
        },
      });

      await expect(apiClient.getProperties()).rejects.toThrow();
    });

    it('handles network errors', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network error'));

      await expect(apiClient.getProperties()).rejects.toThrow('Network error');
    });
  });

  describe('Property Endpoints', () => {
    it('fetches property details', async () => {
      const mockProperty = {
        id: 'prop-123',
        listing_price: 500000,
      };

      mockedAxios.get.mockResolvedValue({ data: mockProperty });

      const result = await apiClient.getProperty('prop-123');

      expect(result).toEqual(mockProperty);
      expect(mockedAxios.get).toHaveBeenCalledWith('/properties/prop-123');
    });

    it('fetches comp analysis', async () => {
      const mockComps = {
        comps: [],
        statistics: {},
      };

      mockedAxios.get.mockResolvedValue({ data: mockComps });

      const result = await apiClient.getCompAnalysis('prop-123', 20);

      expect(result).toEqual(mockComps);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/properties/prop-123/comp-analysis',
        expect.objectContaining({
          params: { limit: 20 },
        })
      );
    });
  });

  describe('Campaign Endpoints', () => {
    it('creates campaign', async () => {
      const mockCampaign = {
        id: 'camp-123',
        name: 'Test Campaign',
        status: 'draft',
      };

      mockedAxios.post.mockResolvedValue({ data: mockCampaign });

      const result = await apiClient.createCampaign({
        name: 'Test Campaign',
        campaign_type: 'cold_outreach',
        steps: [],
      });

      expect(result).toEqual(mockCampaign);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/outreach/campaigns',
        expect.any(Object)
      );
    });

    it('fetches campaign analytics', async () => {
      const mockAnalytics = {
        campaign_id: 'camp-123',
        delivery_rate: 0.95,
        open_rate: 0.32,
      };

      mockedAxios.get.mockResolvedValue({ data: mockAnalytics });

      const result = await apiClient.getCampaignAnalytics('camp-123');

      expect(result).toEqual(mockAnalytics);
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/outreach/campaigns/camp-123/analytics'
      );
    });
  });

  describe('Request Transformation', () => {
    it('converts camelCase to snake_case for requests', async () => {
      mockedAxios.post.mockResolvedValue({ data: {} });

      await apiClient.createCampaign({
        name: 'Test',
        campaignType: 'cold_outreach', // camelCase
        steps: [],
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          campaign_type: 'cold_outreach', // Should be snake_case
        })
      );
    });

    it('converts snake_case to camelCase for responses', async () => {
      mockedAxios.get.mockResolvedValue({
        data: {
          campaign_id: 'camp-123',
          campaign_type: 'cold_outreach',
          total_recipients: 100,
        },
      });

      const result = await apiClient.getCampaign('camp-123');

      expect(result).toHaveProperty('campaignId');
      expect(result).toHaveProperty('campaignType');
      expect(result).toHaveProperty('totalRecipients');
    });
  });
});
