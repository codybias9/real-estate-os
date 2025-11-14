import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'
import type { AuthTokens } from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ============================================================================
// AXIOS INSTANCE
// ============================================================================

const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================================================
// REQUEST INTERCEPTOR
// ============================================================================

api.interceptors.request.use(
  (config) => {
    // Get auth token from localStorage
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        if (state?.tokens?.access_token) {
          config.headers.Authorization = `Bearer ${state.tokens.access_token}`
        }
      } catch (error) {
        console.error('Failed to parse auth storage:', error)
      }
    }

    // Add If-None-Match header for caching (if ETag exists)
    const cacheKey = `etag:${config.url}`
    const cachedETag = sessionStorage.getItem(cacheKey)
    if (cachedETag && config.method === 'get') {
      config.headers['If-None-Match'] = cachedETag
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ============================================================================
// RESPONSE INTERCEPTOR
// ============================================================================

api.interceptors.response.use(
  (response) => {
    // Cache ETag for future requests
    if (response.headers.etag) {
      const cacheKey = `etag:${response.config.url}`
      sessionStorage.setItem(cacheKey, response.headers.etag)
    }

    return response
  },
  async (error: AxiosError) => {
    // Handle 401 Unauthorized - token expired
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('auth-storage')
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login'
      }
    }

    // Handle 304 Not Modified - use cached data
    if (error.response?.status === 304) {
      // Return cached data from previous request
      // This is handled by browser cache
      return error.response
    }

    // Handle rate limiting (429)
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after']
      console.warn(`Rate limited. Retry after ${retryAfter} seconds`)
    }

    return Promise.reject(error)
  }
)

// ============================================================================
// API ENDPOINTS
// ============================================================================

export const apiClient = {
  // ============================================================================
  // AUTHENTICATION
  // ============================================================================

  auth: {
    login: async (email: string, password: string) => {
      const response = await api.post<AuthTokens>('/auth/login', { email, password })
      return response.data
    },

    register: async (data: {
      email: string
      password: string
      full_name: string
      team_name: string
    }) => {
      const response = await api.post('/auth/register', data)
      return response.data
    },

    getCurrentUser: async () => {
      const response = await api.get('/auth/me')
      return response.data
    },

    refreshToken: async () => {
      const response = await api.post<AuthTokens>('/auth/refresh')
      return response.data
    },
  },

  // ============================================================================
  // PROPERTIES
  // ============================================================================

  properties: {
    list: async (params?: {
      team_id?: number
      stage?: string
      assigned_user_id?: number
      skip?: number
      limit?: number
    }) => {
      const response = await api.get('/properties', { params })
      return response.data
    },

    get: async (id: number) => {
      const response = await api.get(`/properties/${id}`)
      return response.data
    },

    create: async (data: any) => {
      const response = await api.post('/properties', data)
      return response.data
    },

    update: async (id: number, data: any) => {
      const response = await api.patch(`/properties/${id}`, data)
      return response.data
    },

    delete: async (id: number) => {
      await api.delete(`/properties/${id}`)
    },

    getTimeline: async (id: number) => {
      const response = await api.get(`/properties/${id}/timeline`)
      return response.data
    },

    getPipelineStats: async (teamId: number) => {
      const response = await api.get(`/properties/stats/pipeline?team_id=${teamId}`)
      return response.data
    },
  },

  // ============================================================================
  // COMMUNICATIONS
  // ============================================================================

  communications: {
    list: async (propertyId: number) => {
      const response = await api.get(`/communications?property_id=${propertyId}`)
      return response.data
    },

    send: async (data: any) => {
      const response = await api.post('/communications/send', data)
      return response.data
    },
  },

  // ============================================================================
  // TEMPLATES
  // ============================================================================

  templates: {
    list: async (teamId: number, stage?: string) => {
      const params = stage
        ? { team_id: teamId, applicable_stage: stage }
        : { team_id: teamId }
      const response = await api.get('/templates', { params })
      return response.data
    },

    get: async (id: string) => {
      const response = await api.get(`/templates/${id}`)
      return response.data
    },

    create: async (data: any) => {
      const response = await api.post('/templates', data)
      return response.data
    },

    update: async (id: string, data: any) => {
      const response = await api.put(`/templates/${id}`, data)
      return response.data
    },

    delete: async (id: string) => {
      await api.delete(`/templates/${id}`)
    },
  },

  // ============================================================================
  // TASKS
  // ============================================================================

  tasks: {
    list: async (propertyId?: number, userId?: number) => {
      const params: any = {}
      if (propertyId) params.property_id = propertyId
      if (userId) params.assigned_user_id = userId

      const response = await api.get('/tasks', { params })
      return response.data
    },

    create: async (data: any) => {
      const response = await api.post('/tasks', data)
      return response.data
    },

    update: async (id: number, data: any) => {
      const response = await api.patch(`/tasks/${id}`, data)
      return response.data
    },
  },

  // ============================================================================
  // WORKFLOW
  // ============================================================================

  workflow: {
    getNextBestActions: async (teamId: number, limit = 10) => {
      const response = await api.get('/workflow/next-best-actions', {
        params: { team_id: teamId, limit },
      })
      return response.data
    },

    getSmartLists: async (teamId: number) => {
      const response = await api.get('/workflow/smart-lists', {
        params: { team_id: teamId },
      })
      return response.data
    },
  },

  // ============================================================================
  // PORTFOLIO
  // ============================================================================

  portfolio: {
    getMetrics: async (teamId: number) => {
      const response = await api.get('/portfolio/metrics', {
        params: { team_id: teamId },
      })
      return response.data
    },

    getDealEconomics: async (propertyId: number) => {
      const response = await api.get(`/portfolio/deal-economics/${propertyId}`)
      return response.data
    },

    getTemplateLeaderboard: async (teamId: number) => {
      const response = await api.get('/portfolio/template-leaderboard', {
        params: { team_id: teamId },
      })
      return response.data
    },
  },

  // ============================================================================
  // QUICK WINS
  // ============================================================================

  quickWins: {
    generateAndSend: async (propertyId: number, templateId: number) => {
      const response = await api.post('/quick-wins/generate-and-send', {
        property_id: propertyId,
        template_id: templateId,
      })
      return response.data
    },

    flagDataIssue: async (propertyId: number, issue: string) => {
      const response = await api.post('/quick-wins/flag-data-issue', {
        property_id: propertyId,
        issue_type: issue,
      })
      return response.data
    },
  },

  // ============================================================================
  // ANALYTICS
  // ============================================================================

  analytics: {
    getDashboard: async (teamId: number) => {
      const response = await api.get('/analytics/dashboard', {
        params: { team_id: teamId },
      })
      return response.data
    },

    getPipeline: async () => {
      const response = await api.get('/analytics/pipeline')
      return response.data
    },

    getRevenue: async (period: string = '30d') => {
      const response = await api.get('/analytics/revenue', {
        params: { period },
      })
      return response.data
    },
  },

  // ============================================================================
  // OPEN DATA
  // ============================================================================

  openData: {
    getSources: async () => {
      const response = await api.get('/open-data/sources')
      return response.data
    },

    enrichProperty: async (propertyId: number, sources?: string[]) => {
      const response = await api.post(`/open-data/enrich-property/${propertyId}`, {
        sources,
      })
      return response.data
    },
  },

  // ============================================================================
  // DATA PROPENSITY (Signals & Provenance)
  // ============================================================================

  dataPropensity: {
    getSignals: async (propertyId: string) => {
      const response = await api.get(`/data-propensity/properties/${propertyId}/signals`)
      return response.data
    },

    getSignalsSummary: async (propertyId: string) => {
      const response = await api.get(`/data-propensity/properties/${propertyId}/signals/summary`)
      return response.data
    },

    getProvenance: async (propertyId: string) => {
      const response = await api.get(`/data-propensity/properties/${propertyId}/provenance`)
      return response.data
    },
  },

  // ============================================================================
  // WORKFLOW (Smart Lists & Next-Best-Actions)
  // ============================================================================

  workflow: {
    getSmartLists: async () => {
      const response = await api.get('/workflow/smart-lists')
      return response.data
    },

    getSmartList: async (id: string) => {
      const response = await api.get(`/workflow/smart-lists/${id}`)
      return response.data
    },

    getNextBestActions: async (propertyId?: string) => {
      const url = propertyId
        ? `/workflow/next-best-actions?property_id=${propertyId}`
        : '/workflow/next-best-actions'
      const response = await api.get(url)
      return response.data
    },

    generateNextBestAction: async (propertyId: string, context?: any) => {
      const response = await api.post('/workflow/next-best-actions/generate', {
        property_id: propertyId,
        context,
      })
      return response.data
    },

    completeAction: async (actionId: string, notes?: string, outcome?: string) => {
      const response = await api.post(`/workflow/next-best-actions/${actionId}/complete`, {
        notes,
        outcome,
      })
      return response.data
    },
  },

  // ============================================================================
  // AUTOMATION (Cadences & Compliance)
  // ============================================================================

  automation: {
    getCadences: async () => {
      const response = await api.get('/automation/cadence-rules')
      return response.data
    },

    getCadence: async (id: string) => {
      const response = await api.get(`/automation/cadence-rules/${id}`)
      return response.data
    },

    toggleCadence: async (id: string, enabled: boolean) => {
      const response = await api.patch(`/automation/cadence-rules/${id}`, { enabled })
      return response.data
    },

    validateSend: async (data: any) => {
      const response = await api.post('/automation/validate-send', data)
      return response.data
    },

    checkDNC: async (phone?: string, email?: string) => {
      const response = await api.post('/automation/dnc/check', {
        phone_number: phone,
        email,
      })
      return response.data
    },

    checkConsent: async (propertyId: string, email?: string, phone?: string) => {
      const response = await api.post('/automation/consent/check', {
        property_id: propertyId,
        email,
        phone_number: phone,
      })
      return response.data
    },
  },

  // ============================================================================
  // DATA ENRICHMENT & SIGNALS
  // ============================================================================

  data: {
    // Enrichment stats
    getEnrichmentStats: async () => {
      const response = await api.get('/data-propensity/enrichment/stats')
      return response.data
    },

    // Property signals
    getPropertySignals: async (propertyId: string, signalType?: string, minStrength?: string) => {
      let url = `/data-propensity/properties/${propertyId}/signals`
      const params = new URLSearchParams()
      if (signalType) params.append('signal_type', signalType)
      if (minStrength) params.append('min_strength', minStrength)
      if (params.toString()) url += `?${params.toString()}`

      const response = await api.get(url)
      return response.data
    },

    getSignalsSummary: async (propertyId: string) => {
      const response = await api.get(`/data-propensity/properties/${propertyId}/signals/summary`)
      return response.data
    },

    getTrendingSignals: async (days: number = 30, limit: number = 10) => {
      const response = await api.get(`/data-propensity/signals/trending?days=${days}&limit=${limit}`)
      return response.data
    },

    // Data provenance
    getPropertyProvenance: async (propertyId: string) => {
      const response = await api.get(`/data-propensity/properties/${propertyId}/provenance`)
      return response.data
    },

    updateDataSource: async (data: any) => {
      const response = await api.post('/data-propensity/provenance/update-source', data)
      return response.data
    },

    // Enrichment jobs
    enrichProperty: async (propertyId: string, dataSources: string[], priority: string = 'normal') => {
      const response = await api.post(`/data-propensity/properties/${propertyId}/enrich`, {
        property_id: propertyId,
        data_sources: dataSources,
        priority,
      })
      return response.data
    },
  },

  // ============================================================================
  // SYSTEM & ADMIN
  // ============================================================================

  system: {
    // System health
    getHealth: async () => {
      const response = await api.get('/system/health')
      return response.data
    },

    getMetrics: async () => {
      const response = await api.get('/system/metrics')
      return response.data
    },

    // Workers and queues
    getWorkers: async () => {
      const response = await api.get('/system/workers')
      return response.data
    },

    getQueues: async () => {
      const response = await api.get('/system/queues')
      return response.data
    },

    // Storage
    getStorage: async () => {
      const response = await api.get('/system/storage')
      return response.data
    },

    // Logs and errors
    getRecentLogs: async (limit: number = 50) => {
      const response = await api.get(`/system/logs/recent?limit=${limit}`)
      return response.data
    },

    getRecentErrors: async (limit: number = 20) => {
      const response = await api.get(`/system/errors/recent?limit=${limit}`)
      return response.data
    },
  },
}

export default api
