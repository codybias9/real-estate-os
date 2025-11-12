/**
 * Tests for API Client
 */

import axios from 'axios';
import { ApiClient } from '@/lib/api-client';
import { PropertyState } from '@/types';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('ApiClient', () => {
  let client: ApiClient;
  let mockCreate: jest.Mock;

  beforeEach(() => {
    mockCreate = jest.fn().mockReturnValue({
      get: jest.fn(),
      post: jest.fn(),
      patch: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    });
    mockedAxios.create = mockCreate;

    client = new ApiClient('http://localhost:8000');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('creates axios instance with correct config', () => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://localhost:8000/v1',
          timeout: 30000,
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('uses environment variable for baseURL if not provided', () => {
      process.env.NEXT_PUBLIC_API_URL = 'http://api.example.com';
      const envClient = new ApiClient();

      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://api.example.com/v1',
        })
      );
    });
  });

  describe('healthCheck', () => {
    it('calls health endpoint', async () => {
      const mockResponse = { data: { status: 'ok' } };
      const mockClient = {
        get: jest.fn().mockResolvedValue(mockResponse),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      };
      mockedAxios.create = jest.fn().mockReturnValue(mockClient);

      const client = new ApiClient();
      const result = await client.healthCheck();

      expect(mockClient.get).toHaveBeenCalledWith('/healthz');
      expect(result).toEqual({ status: 'ok' });
    });
  });

  describe('getProperties', () => {
    it('calls properties endpoint with filters', async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 0,
          page: 1,
          per_page: 20,
          pages: 0,
        },
      };
      const mockClient = {
        get: jest.fn().mockResolvedValue(mockResponse),
        interceptors: {
          request: { use: jest.fn() },
          response: { use: jest.fn() },
        },
      };
      mockedAxios.create = jest.fn().mockReturnValue(mockClient);

      const client = new ApiClient();
      const filters = {
        state: [PropertyState.SCORED],
        min_score: 70,
        page: 1,
        per_page: 20,
      };

      await client.getProperties(filters);

      expect(mockClient.get).toHaveBeenCalledWith('/properties', {
        params: filters,
      });
    });
  });

  describe('subscribeToTimeline', () => {
    it('creates EventSource with correct URL', () => {
      // Mock EventSource
      const mockEventSource = {
        addEventListener: jest.fn(),
        close: jest.fn(),
        onerror: null,
      };
      global.EventSource = jest.fn().mockReturnValue(mockEventSource) as any;

      const client = new ApiClient('http://localhost:8000');
      const onEvent = jest.fn();
      const onError = jest.fn();

      const eventSource = client.subscribeToTimeline('prop-123', onEvent, onError);

      expect(global.EventSource).toHaveBeenCalledWith(
        'http://localhost:8000/v1/properties/prop-123/timeline/stream'
      );
      expect(mockEventSource.addEventListener).toHaveBeenCalledWith(
        'timeline-event',
        expect.any(Function)
      );
    });
  });
});
