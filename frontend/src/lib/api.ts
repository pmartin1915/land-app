// API client for Alabama Auction Watcher FastAPI backend
// Configuration loaded from environment variables

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'

// Extend Axios config to include metadata for performance tracking and retry count
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: { startTime: number }
    _retryCount?: number
  }
}

import {
  Property,
  County,
  AISuggestion,
  UserProfile,
  PropertyApplication,
  APIResponse,
  PaginatedResponse,
  APIError,
  SearchParams,
  CSVImportMapping,
  CSVImportResult,
  PropertyFilters,
  ExportJob,
  SyncLog,
} from '../types'
import { config } from '../config'
import { globalCache } from './cache'

// API Response Types for endpoints without specific types
export interface PropertyListResponse {
  properties: Property[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PropertyStatsResponse {
  total_properties: number
  total_value: number
  avg_investment_score: number
  by_state: Record<string, number>
  by_status: Record<string, number>
  price_distribution?: { ranges: string[]; counts: number[] }
  score_distribution?: Record<string, number>
  top_counties?: { name: string; avg_investment_score: number }[]
  activity_timeline?: { dates: string[]; new_properties: number[] }
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down'
  timestamp: string
  version?: string
}

export interface DetailedHealthResponse extends HealthResponse {
  database: boolean
  cache: boolean
  api_response_time?: number
  memory_usage?: number
}

export interface CacheStatsResponse {
  hits: number
  misses: number
  size: number
  hit_ratio: number
}

export interface SyncStatusResponse {
  status: 'synced' | 'syncing' | 'error'
  last_sync: string
  pending_changes: number
}

export interface CSVPreviewResponse {
  headers: string[]
  rows: string[][]
  total_rows: number
  mapping?: CSVImportMapping
}

export interface ImportHistoryItem {
  id: string
  filename: string
  created_at: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  imported: number
  duplicates: number
  errors: number
}

export interface WatchlistStatsResponse {
  watched: number
  rated: number
  dismissed: number
  with_notes: number
  total_interactions: number
}

// First Deal Pipeline Types
export type FirstDealStage = 'research' | 'bid' | 'won' | 'quiet_title' | 'sold' | 'holding'

export interface FirstDealResponse {
  property: Property | null
  interaction: {
    id: string
    device_id: string
    property_id: string
    is_watched: boolean
    star_rating?: number
    user_notes?: string
    dismissed: boolean
    is_first_deal: boolean
    first_deal_stage?: FirstDealStage
    first_deal_assigned_at?: string
    first_deal_updated_at?: string
    created_at?: string
    updated_at?: string
  } | null
  stage: FirstDealStage | null
  has_first_deal: boolean
}

// API Configuration from centralized config
const API_BASE_URL = config.api.fullUrl
const API_TIMEOUT = config.api.timeout

// Retry configuration for connection resilience
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,      // 1 second initial delay
  maxDelay: 10000,      // 10 second max delay
  backoffMultiplier: 2, // Exponential backoff
  retryableErrors: [
    'ECONNREFUSED',
    'ECONNRESET',
    'ETIMEDOUT',
    'ENOTFOUND',
    'ERR_NETWORK',
    'Network Error',
  ],
  retryableStatuses: [429, 502, 503, 504], // Rate Limited, Bad Gateway, Service Unavailable, Gateway Timeout
  rateLimitDelay: 60000, // 60 second cooldown for rate limits
}

// Connection state management
class ConnectionManager {
  private static isOnline: boolean = true
  private static listeners: Set<(online: boolean) => void> = new Set()
  private static reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private static reconnectAttempts: number = 0
  private static readonly MAX_RECONNECT_ATTEMPTS = 10
  private static failureCount: number = 0
  private static readonly FAILURE_THRESHOLD = 2 // Require 2 consecutive failures before marking offline

  static initialize(): void {
    // Don't re-initialize
    if (this.listeners.size > 0) return

    // Monitor browser online/offline events
    window.addEventListener('online', () => this.setOnline(true))
    window.addEventListener('offline', () => this.setOnline(false))
  }

  static setOnline(online: boolean): void {
    if (online) {
      // Reset failure count on success
      this.failureCount = 0
      const wasOffline = !this.isOnline
      this.isOnline = true

      if (wasOffline) {
        console.log('[ConnectionManager] Connection restored')
        this.reconnectAttempts = 0
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer)
          this.reconnectTimer = null
        }
        this.notifyListeners()
      }
    } else {
      // Require multiple failures before marking offline
      this.failureCount++
      if (this.failureCount < this.FAILURE_THRESHOLD) {
        console.log(`[ConnectionManager] Connection failure ${this.failureCount}/${this.FAILURE_THRESHOLD}, not marking offline yet`)
        return
      }

      if (this.isOnline) {
        console.warn('[ConnectionManager] Connection lost')
        this.isOnline = false
        this.notifyListeners()
      }
    }
  }

  static getStatus(): boolean {
    return this.isOnline
  }

  static subscribe(callback: (online: boolean) => void): () => void {
    this.listeners.add(callback)
    return () => this.listeners.delete(callback)
  }

  private static notifyListeners(): void {
    this.listeners.forEach(cb => cb(this.isOnline))
  }

  static scheduleReconnect(onReconnect: () => Promise<boolean>): void {
    if (this.reconnectTimer || this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      return
    }

    const delay = Math.min(
      RETRY_CONFIG.baseDelay * Math.pow(RETRY_CONFIG.backoffMultiplier, this.reconnectAttempts),
      RETRY_CONFIG.maxDelay
    )

    console.log(`[ConnectionManager] Scheduling reconnect attempt ${this.reconnectAttempts + 1} in ${delay}ms`)

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null
      this.reconnectAttempts++

      try {
        const success = await onReconnect()
        if (success) {
          this.setOnline(true)
        } else {
          this.scheduleReconnect(onReconnect)
        }
      } catch {
        this.scheduleReconnect(onReconnect)
      }
    }, delay)
  }

  static resetReconnectAttempts(): void {
    this.reconnectAttempts = 0
  }
}

// Initialize connection manager
ConnectionManager.initialize()

// Authentication Manager for automatic token handling
class AuthManager {
  private static readonly TOKEN_KEY = config.auth.tokenKey
  private static readonly REFRESH_TOKEN_KEY = config.auth.refreshTokenKey
  private static readonly TOKEN_EXPIRES_KEY = config.auth.tokenExpiresKey

  // Generate unique device ID for this browser/app instance
  private static getDeviceId(): string {
    let deviceId = localStorage.getItem(config.auth.deviceIdKey)
    if (!deviceId) {
      // Use crypto.randomUUID() for privacy-preserving unique ID
      deviceId = crypto.randomUUID()
      localStorage.setItem(config.auth.deviceIdKey, deviceId)
    }
    return deviceId
  }

  // Check if current token is expired
  private static isTokenExpired(): boolean {
    const expires = localStorage.getItem(this.TOKEN_EXPIRES_KEY)
    if (!expires) return true

    const expirationTime = parseInt(expires)
    const currentTime = Date.now() / 1000 // Convert to seconds
    const bufferTime = 60 // Refresh 1 minute before expiration

    return currentTime >= (expirationTime - bufferTime)
  }

  // Request new device token from backend
  private static async requestDeviceToken(): Promise<string> {
    try {
      console.log('Requesting new device token...')

      const deviceId = this.getDeviceId()
      const response = await axios.post(`${API_BASE_URL}/auth/device/token`, {
        device_id: deviceId,
        app_version: '1.0.0',
        device_name: 'Web Client',
      })

      const tokenData = response.data

      // Store token and expiration
      const token = tokenData.access_token
      const refreshToken = tokenData.refresh_token
      const expiresIn = tokenData.expires_in || 3600 // Default 1 hour
      const expirationTime = Math.floor(Date.now() / 1000) + expiresIn

      localStorage.setItem(this.TOKEN_KEY, token)
      localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
      localStorage.setItem(this.TOKEN_EXPIRES_KEY, expirationTime.toString())

      console.log('Device token obtained successfully')
      return token

    } catch (error: unknown) {
      console.error('Failed to request device token:', error)

      // Log detailed error information for debugging
      const axiosError = error as AxiosError
      if (axiosError.response) {
        console.error('Response status:', axiosError.response.status)
        console.error('Response data:', axiosError.response.data)
      }

      const message = error instanceof Error ? error.message : 'Unknown error'
      throw new Error(`Authentication failed: ${message}`)
    }
  }

  // Refresh token using refresh token
  private static async refreshToken(): Promise<string> {
    try {
      const refreshToken = localStorage.getItem(this.REFRESH_TOKEN_KEY)
      if (!refreshToken) {
        throw new Error('No refresh token available')
      }

      console.log('Refreshing token...')

      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken
      })

      const tokenData = response.data
      const token = tokenData.access_token
      const newRefreshToken = tokenData.refresh_token
      const expiresIn = tokenData.expires_in || 3600
      const expirationTime = Math.floor(Date.now() / 1000) + expiresIn

      localStorage.setItem(this.TOKEN_KEY, token)
      localStorage.setItem(this.REFRESH_TOKEN_KEY, newRefreshToken)
      localStorage.setItem(this.TOKEN_EXPIRES_KEY, expirationTime.toString())

      console.log('Token refreshed successfully')
      return token

    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error'
      console.warn('Token refresh failed, requesting new token:', message)
      // If refresh fails, request a new token
      return await this.requestDeviceToken()
    }
  }

  // Ensure we have a valid authentication token
  public static async ensureValidToken(): Promise<string> {
    const currentToken = localStorage.getItem(this.TOKEN_KEY)

    // If no token or token is expired, get a new one
    if (!currentToken || this.isTokenExpired()) {
      try {
        // Try to refresh first if we have a refresh token
        const refreshToken = localStorage.getItem(this.REFRESH_TOKEN_KEY)
        if (refreshToken && currentToken) {
          return await this.refreshToken()
        } else {
          return await this.requestDeviceToken()
        }
      } catch (error) {
        // If all else fails, request a new token
        return await this.requestDeviceToken()
      }
    }

    return currentToken
  }

  // Clear all authentication data
  public static clearAuth(): void {
    localStorage.removeItem(this.TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
    localStorage.removeItem(this.TOKEN_EXPIRES_KEY)
  }

  // Get current token status for debugging
  public static getAuthStatus(): { hasToken: boolean; isExpired: boolean; expiresAt: string | null; deviceId: string } {
    const token = localStorage.getItem(this.TOKEN_KEY)
    const expires = localStorage.getItem(this.TOKEN_EXPIRES_KEY)
    const deviceId = this.getDeviceId()

    return {
      hasToken: !!token,
      isExpired: this.isTokenExpired(),
      expiresAt: expires ? new Date(parseInt(expires) * 1000).toLocaleString() : null,
      deviceId
    }
  }
}

// Helper to determine if an error is retryable
function isRetryableError(error: AxiosError): boolean {
  // Network errors (no response)
  if (!error.response) {
    const message = error.message || ''
    const code = error.code || ''
    return RETRY_CONFIG.retryableErrors.some(
      e => message.includes(e) || code.includes(e)
    )
  }

  // Server errors that indicate temporary unavailability
  return RETRY_CONFIG.retryableStatuses.includes(error.response.status)
}

// Calculate delay with exponential backoff and jitter
function getRetryDelay(retryCount: number): number {
  const baseDelay = RETRY_CONFIG.baseDelay * Math.pow(RETRY_CONFIG.backoffMultiplier, retryCount)
  const jitter = Math.random() * 0.3 * baseDelay // Add up to 30% jitter
  return Math.min(baseDelay + jitter, RETRY_CONFIG.maxDelay)
}

// Sleep helper
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// Create axios instance with default configuration
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // Request interceptor for automatic authentication
  client.interceptors.request.use(
    async (config) => {
      try {
        // Automatically ensure we have a valid token
        const token = await AuthManager.ensureValidToken()
        config.headers.Authorization = `Bearer ${token}`

        // Add request timestamp for debugging
        config.metadata = { startTime: Date.now() }

        return config
      } catch (error: unknown) {
        console.error('Authentication failed in request interceptor:', error)
        // Continue without auth - some endpoints might not require it
        config.metadata = { startTime: Date.now() }
        return config
      }
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor for error handling, logging, and automatic retry
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // Mark connection as online on successful response
      ConnectionManager.setOnline(true)
      ConnectionManager.resetReconnectAttempts()

      // Log performance metrics if in development
      if (process.env.NODE_ENV === 'development') {
        const duration = Date.now() - response.config.metadata?.startTime
        console.log(`API ${response.config.method?.toUpperCase()} ${response.config.url}: ${duration}ms`)
      }

      return response
    },
    async (error: AxiosError<APIError>) => {
      const originalRequest = error.config as AxiosError['config'] & { _retryCount?: number }
      const retryCount = originalRequest?._retryCount || 0

      // Handle connection/network errors with retry
      if (isRetryableError(error) && retryCount < RETRY_CONFIG.maxRetries) {
        originalRequest._retryCount = retryCount + 1
        const delay = getRetryDelay(retryCount)

        console.warn(
          `[API] Connection error (attempt ${retryCount + 1}/${RETRY_CONFIG.maxRetries}), ` +
          `retrying in ${Math.round(delay)}ms...`,
          { url: originalRequest.url, error: error.message || error.code }
        )

        // Mark as potentially offline if this is a network error
        if (!error.response) {
          ConnectionManager.setOnline(false)
        }

        await sleep(delay)

        try {
          const result = await client(originalRequest)
          // Success - we're back online
          ConnectionManager.setOnline(true)
          return result
        } catch (retryError) {
          // If all retries exhausted, schedule background reconnection
          if (retryCount + 1 >= RETRY_CONFIG.maxRetries) {
            ConnectionManager.scheduleReconnect(async () => {
              try {
                // Use systemClient for root-level health endpoint
                await systemClient.get('/health', { timeout: 5000 })
                return true
              } catch {
                return false
              }
            })
          }
          throw retryError
        }
      }

      // Handle 429 Rate Limited errors with longer cooldown
      if (error.response?.status === 429 && retryCount < 1) {
        originalRequest._retryCount = retryCount + 1
        console.warn(
          `[API] Rate limited (429), waiting ${RETRY_CONFIG.rateLimitDelay / 1000} seconds before retry...`
        )
        await sleep(RETRY_CONFIG.rateLimitDelay)
        return client(originalRequest)
      }

      // Handle 401 Unauthorized errors with automatic retry (max 1 retry)
      if (error.response?.status === 401 && retryCount < 1) {
        originalRequest._retryCount = retryCount + 1

        try {
          console.warn('Authentication failed, attempting to refresh token...')

          // Clear current auth and get a new token
          AuthManager.clearAuth()
          const newToken = await AuthManager.ensureValidToken()

          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`

          console.log('Retrying request with new token')
          return client(originalRequest)

        } catch (authError: unknown) {
          console.error('Failed to refresh authentication:', authError)

          // If auth refresh fails, clear everything and let the request fail
          AuthManager.clearAuth()

          // Create a user-friendly error
          const friendlyError = new Error('Authentication required. Please refresh the page.')
          friendlyError.name = 'AuthenticationError'
          return Promise.reject(friendlyError)
        }
      }

      // Log error details
      console.error('API Error:', {
        status: error.response?.status,
        message: error.response?.data?.message || error.message,
        url: error.config?.url,
        method: error.config?.method,
        retryCount,
      })

      // Transform backend errors to frontend format
      if (error.response?.data) {
        const apiError = error.response.data
        const transformedError = new Error(apiError.message || 'An API error occurred') as Error & { status: number; details: APIError }
        transformedError.name = 'APIError'
        transformedError.status = error.response.status
        transformedError.details = apiError
        return Promise.reject(transformedError)
      }

      return Promise.reject(error)
    }
  )

  return client
}

// Initialize API client
const apiClient = createApiClient()

// Create separate client for root-level system endpoints (no /api/v1 prefix)
// Health check, cache stats, etc. are served at root level by the backend
const createSystemClient = (): AxiosInstance => {
  return axios.create({
    baseURL: config.api.baseUrl,  // Uses baseUrl, not fullUrl (no /api/v1)
    timeout: 5000,
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

const systemClient = createSystemClient()

/**
 * Filter mapping configuration: frontend key -> backend key or transform function.
 * Adding a new filter only requires adding an entry here - prevents forgotten filters.
 */
type FilterMapping = string | ((filters: PropertyFilters) => Record<string, unknown>)

const FILTER_MAPPINGS: Record<keyof PropertyFilters, FilterMapping> = {
  // Simple 1:1 mappings (frontend camelCase -> backend snake_case)
  state: 'state',
  county: 'county',
  waterOnly: 'water_features',
  minInvestmentScore: 'min_investment_score',
  minCountyMarketScore: 'min_county_market_score',
  minGeographicScore: 'min_geographic_score',
  minMarketTimingScore: 'min_market_timing_score',
  minTotalDescriptionScore: 'min_total_description_score',
  minRoadAccessScore: 'min_road_access_score',
  minYearSold: 'min_year_sold',
  excludeDeltaRegion: 'exclude_delta_region',
  createdAfter: 'created_after',
  hasDocuments: 'has_documents',
  // Multi-state scoring filters
  maxEffectiveCost: 'max_effective_cost',
  minBuyHoldScore: 'min_buy_hold_score',

  // Complex mappings (ranges that expand to multiple params)
  priceRange: (f) => f.priceRange ? {
    min_price: f.priceRange[0],
    max_price: f.priceRange[1]
  } : {},
  acreageRange: (f) => f.acreageRange ? {
    min_acreage: f.acreageRange[0],
    max_acreage: f.acreageRange[1]
  } : {},
  dateRange: (f) => f.dateRange ? {
    date_from: f.dateRange[0],
    date_to: f.dateRange[1]
  } : {},

  // Array mappings
  counties: 'counties',
  status: 'status',
}

/**
 * Flatten frontend filters to backend query params.
 * Uses declarative mapping to ensure all filters are transmitted.
 */
function flattenFilters(filters: PropertyFilters): Record<string, unknown> {
  const flatParams: Record<string, unknown> = {}

  for (const [frontendKey, mapping] of Object.entries(FILTER_MAPPINGS)) {
    const value = (filters as Record<string, unknown>)[frontendKey]

    // Skip undefined/null values
    if (value === undefined || value === null) continue

    if (typeof mapping === 'function') {
      // Complex mapping - function returns multiple params
      Object.assign(flatParams, mapping(filters))
    } else {
      // Simple 1:1 mapping
      flatParams[mapping] = value
    }
  }

  return flatParams
}

// Generic API response handler
const handleResponse = <T>(response: AxiosResponse<APIResponse<T> | T>): T => {
  // Handle both wrapped and unwrapped responses
  if (response.data && typeof response.data === 'object' && 'data' in response.data) {
    return (response.data as APIResponse<T>).data
  }
  return response.data as T
}

// Properties API
export const propertiesApi = {
  // Get all properties with filtering and pagination
  getProperties: async (params?: SearchParams): Promise<PaginatedResponse<Property>> => {
    // Flatten filters into top-level query params for FastAPI compatibility
    const flatParams: Record<string, unknown> = {}
    if (params) {
      if (params.q) flatParams.search_query = params.q
      if (params.page) flatParams.page = params.page
      if (params.per_page) flatParams.page_size = params.per_page
      if (params.sort_by) flatParams.sort_by = params.sort_by
      if (params.sort_order) flatParams.sort_order = params.sort_order

      // Use declarative mapping for all filter parameters
      if (params.filters) {
        Object.assign(flatParams, flattenFilters(params.filters))
      }
    }
    const response = await apiClient.get('/properties/', { params: flatParams })
    const data = handleResponse(response)

    // Map backend PropertyListResponse to frontend PaginatedResponse
    // Backend uses: properties, total_count, page_size, total_pages, has_previous
    // Frontend expects: items, total, per_page, pages, has_prev
    if ('properties' in data) {
      const backendData = data as PropertyListResponse
      return {
        items: backendData.properties,
        total: backendData.total_count,
        page: backendData.page,
        per_page: backendData.page_size,
        pages: backendData.total_pages,
        has_next: backendData.has_next,
        has_prev: backendData.has_previous,
      }
    }

    return data
  },

  // Get single property by ID
  getProperty: async (id: string): Promise<Property> => {
    const response = await apiClient.get(`/properties/${id}`)
    return handleResponse(response)
  },

  // Create new property
  createProperty: async (property: Partial<Property>): Promise<Property> => {
    const response = await apiClient.post('/properties/', property)
    return handleResponse(response)
  },

  // Update existing property
  updateProperty: async (id: string, property: Partial<Property>): Promise<Property> => {
    const response = await apiClient.put(`/properties/${id}`, property)
    return handleResponse(response)
  },

  // Delete property
  deleteProperty: async (id: string): Promise<void> => {
    await apiClient.delete(`/properties/${id}`)
  },

  // Bulk operations
  bulkUpdateProperties: async (ids: string[], updates: Partial<Property>): Promise<Property[]> => {
    const response = await apiClient.patch('/properties/bulk', { ids, updates })
    return handleResponse(response)
  },

  // Search properties
  searchProperties: async (query: string, filters?: PropertyFilters): Promise<Property[]> => {
    const flatFilters = filters ? flattenFilters(filters) : {}
    const response = await apiClient.get('/properties/search', {
      params: { q: query, ...flatFilters }
    })
    return handleResponse(response)
  },

  // Get property statistics
  getPropertyStats: async (filters?: PropertyFilters): Promise<PropertyStatsResponse> => {
    const response = await apiClient.get('/properties/stats', { params: filters })
    return handleResponse(response)
  },

  // Update property research status
  updatePropertyStatus: async (id: string, status: string, notes?: string): Promise<Property> => {
    const response = await apiClient.patch(`/properties/${id}/status`, {
      status,
      triage_notes: notes,
      device_id: localStorage.getItem('device_id') || 'web-client'
    })
    return handleResponse(response)
  },

  // Get workflow statistics (counts by status)
  getWorkflowStats: async (): Promise<{
    new: number
    reviewing: number
    bid_ready: number
    rejected: number
    purchased: number
    total: number
  }> => {
    const response = await apiClient.get('/properties/workflow/stats')
    return handleResponse(response)
  },
}

// Counties API
export const countiesApi = {
  // Get all counties
  getCounties: async (): Promise<County[]> => {
    const response = await apiClient.get('/counties/')
    return handleResponse(response)
  },

  // Get single county by code
  getCounty: async (code: string): Promise<County> => {
    const response = await apiClient.get(`/counties/${code}`)
    return handleResponse(response)
  },

  // Get county statistics
  getCountyStats: async (code?: string): Promise<PropertyStatsResponse> => {
    const endpoint = code ? `/counties/${code}/stats` : '/counties/stats'
    const response = await apiClient.get(endpoint)
    return handleResponse(response)
  },
}

// AI Suggestions API
export const aiApi = {
  // Get AI suggestions for property
  getPropertySuggestions: async (propertyId: string): Promise<AISuggestion[]> => {
    const response = await apiClient.get(`/ai/suggestions/property/${propertyId}`)
    return handleResponse(response)
  },

  // Apply AI suggestion
  applySuggestion: async (suggestionId: string): Promise<AISuggestion> => {
    const response = await apiClient.post(`/ai/suggestions/${suggestionId}/apply`)
    return handleResponse(response)
  },

  // Reject AI suggestion
  rejectSuggestion: async (suggestionId: string, reason?: string): Promise<void> => {
    await apiClient.post(`/ai/suggestions/${suggestionId}/reject`, { reason })
  },

  // Get triage queue
  getTriageQueue: async (): Promise<AISuggestion[]> => {
    const response = await apiClient.get('/ai/triage')
    return handleResponse(response)
  },

  // Bulk apply suggestions
  bulkApplySuggestions: async (suggestionIds: string[]): Promise<AISuggestion[]> => {
    const response = await apiClient.post('/ai/suggestions/bulk-apply', { suggestion_ids: suggestionIds })
    return handleResponse(response)
  },
}

// CSV Import API
export const importApi = {
  // Upload and preview CSV
  previewCSV: async (file: File, mapping?: CSVImportMapping): Promise<CSVPreviewResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (mapping) {
      formData.append('mapping', JSON.stringify(mapping))
    }

    const response = await apiClient.post('/import/csv/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return handleResponse(response)
  },

  // Import CSV with mapping
  importCSV: async (file: File, mapping: CSVImportMapping): Promise<CSVImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mapping', JSON.stringify(mapping))

    const response = await apiClient.post('/import/csv/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return handleResponse(response)
  },

  // Get import history
  getImportHistory: async (): Promise<ImportHistoryItem[]> => {
    const response = await apiClient.get('/import/history')
    return handleResponse(response)
  },
}

// Export API
export const exportApi = {
  // Export properties to CSV
  exportToCSV: async (filters?: PropertyFilters, columns?: string[]): Promise<ExportJob> => {
    const response = await apiClient.post('/export/csv', { filters, columns })
    return handleResponse(response)
  },

  // Export properties to JSON
  exportToJSON: async (filters?: PropertyFilters): Promise<ExportJob> => {
    const response = await apiClient.post('/export/json', { filters })
    return handleResponse(response)
  },

  // Get export job status
  getExportJob: async (jobId: string): Promise<ExportJob> => {
    const response = await apiClient.get(`/export/jobs/${jobId}`)
    return handleResponse(response)
  },

  // Download export file
  downloadExport: async (jobId: string): Promise<Blob> => {
    const response = await apiClient.get(`/export/jobs/${jobId}/download`, {
      responseType: 'blob'
    })
    return response.data
  },
}

// User Profile API
export const userApi = {
  // Get user profile
  getProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get('/user/profile')
    return handleResponse(response)
  },

  // Update user profile
  updateProfile: async (profile: Partial<UserProfile>): Promise<UserProfile> => {
    const response = await apiClient.put('/user/profile', profile)
    return handleResponse(response)
  },

  // Get user preferences
  getPreferences: async (): Promise<Record<string, unknown>> => {
    const response = await apiClient.get('/user/preferences')
    return handleResponse(response)
  },

  // Update user preferences
  updatePreferences: async (preferences: Record<string, unknown>): Promise<Record<string, unknown>> => {
    const response = await apiClient.put('/user/preferences', preferences)
    return handleResponse(response)
  },
}

// Application Assistant API
export const applicationApi = {
  // Get property applications
  getApplications: async (): Promise<PropertyApplication[]> => {
    const response = await apiClient.get('/applications/')
    return handleResponse(response)
  },

  // Create property application
  createApplication: async (application: Partial<PropertyApplication>): Promise<PropertyApplication> => {
    const response = await apiClient.post('/applications/', application)
    return handleResponse(response)
  },

  // Update application
  updateApplication: async (id: string, application: Partial<PropertyApplication>): Promise<PropertyApplication> => {
    const response = await apiClient.put(`/applications/${id}`, application)
    return handleResponse(response)
  },

  // Delete application
  deleteApplication: async (id: string): Promise<void> => {
    await apiClient.delete(`/applications/${id}`)
  },

  // Generate application forms
  generateForms: async (applicationIds: string[]): Promise<{ forms: string[]; generated_count: number }> => {
    const response = await apiClient.post('/applications/generate-forms', { application_ids: applicationIds })
    return handleResponse(response)
  },
}

// Helper to invalidate portfolio caches when watchlist changes
const invalidatePortfolioCaches = async () => {
  await Promise.all([
    globalCache.remove('portfolio-summary'),
    globalCache.remove('portfolio-geographic'),
    globalCache.remove('portfolio-scores'),
    globalCache.remove('portfolio-risk'),
    globalCache.remove('portfolio-performance'),
  ])
}

// Watchlist API
export const watchlistApi = {
  // Get watchlist with pagination
  getWatchlist: async (page: number = 1, pageSize: number = 20): Promise<PaginatedResponse<Property>> => {
    const response = await apiClient.get('/watchlist', {
      params: { page, page_size: pageSize }
    })
    return handleResponse(response)
  },

  // Get watchlist statistics
  getStats: async (): Promise<WatchlistStatsResponse> => {
    const response = await apiClient.get('/watchlist/stats')
    return handleResponse(response)
  },

  // Get bulk watch status for multiple properties
  getBulkStatus: async (propertyIds: string[]): Promise<Record<string, boolean>> => {
    const response = await apiClient.get('/watchlist/bulk-status', {
      params: { property_ids: propertyIds.join(',') }
    })
    return handleResponse(response)
  },

  // Toggle watch status for a property
  toggleWatch: async (propertyId: string): Promise<{ is_watched: boolean }> => {
    const response = await apiClient.post(`/watchlist/property/${propertyId}/watch`)
    const result = handleResponse(response)
    await invalidatePortfolioCaches()
    return result
  },

  // Update property interaction (rating, notes)
  updateInteraction: async (propertyId: string, data: { star_rating?: number; user_notes?: string }): Promise<{ id: string; star_rating?: number; user_notes?: string }> => {
    const response = await apiClient.put(`/watchlist/property/${propertyId}`, data)
    const result = handleResponse(response)
    await invalidatePortfolioCaches()
    return result
  },

  // First Deal Tracking
  // Get the user's current first deal property
  getFirstDeal: async (): Promise<FirstDealResponse> => {
    const response = await apiClient.get('/watchlist/first-deal')
    return handleResponse(response)
  },

  // Set a property as the first deal
  setFirstDeal: async (propertyId: string): Promise<{ property_id: string; is_first_deal: boolean; stage: string }> => {
    const response = await apiClient.post(`/watchlist/property/${propertyId}/set-first-deal`)
    const result = handleResponse(response)
    await invalidatePortfolioCaches()
    return result
  },

  // Update the pipeline stage for the first deal
  updateFirstDealStage: async (stage: FirstDealStage): Promise<{ property_id: string; stage: string; updated_at: string }> => {
    const response = await apiClient.put('/watchlist/first-deal/stage', { stage })
    const result = handleResponse(response)
    await invalidatePortfolioCaches()
    return result
  },

  // Remove the first deal assignment
  removeFirstDeal: async (): Promise<{ property_id: string; message: string }> => {
    const response = await apiClient.delete('/watchlist/first-deal')
    const result = handleResponse(response)
    await invalidatePortfolioCaches()
    return result
  },
}

// Sync API
export const syncApi = {
  // Get sync status
  getSyncStatus: async (): Promise<SyncStatusResponse> => {
    const response = await apiClient.get('/sync/status')
    return handleResponse(response)
  },

  // Trigger manual sync
  triggerSync: async (): Promise<SyncLog> => {
    const response = await apiClient.post('/sync/trigger')
    return handleResponse(response)
  },

  // Get sync logs
  getSyncLogs: async (): Promise<SyncLog[]> => {
    const response = await apiClient.get('/sync/logs')
    return handleResponse(response)
  },
}

// Health and monitoring API (uses systemClient - root-level endpoints, no /api/v1 prefix)
export const systemApi = {
  // Check API health
  getHealth: async (): Promise<HealthResponse> => {
    const response = await systemClient.get('/health')
    return response.data
  },

  // Get detailed health
  getDetailedHealth: async (): Promise<DetailedHealthResponse> => {
    const response = await systemClient.get('/health/detailed')
    return response.data
  },

  // Get cache statistics
  getCacheStats: async (): Promise<CacheStatsResponse> => {
    const response = await systemClient.get('/cache/stats')
    return response.data
  },

  // Warm cache
  warmCache: async (): Promise<{ warmed: boolean; items_cached: number }> => {
    const response = await systemClient.post('/cache/warm')
    return response.data
  },
}

// Portfolio Analytics API
import {
  PortfolioSummaryResponse,
  GeographicBreakdownResponse,
  ScoreDistributionResponse,
  RiskAnalysisResponse,
  PerformanceTrackingResponse,
  PortfolioAnalyticsExport,
} from '../types/portfolio'

export const portfolioApi = {
  // Get portfolio summary metrics
  getSummary: async (): Promise<PortfolioSummaryResponse> => {
    const response = await apiClient.get('/portfolio/summary')
    return handleResponse(response)
  },

  // Get geographic breakdown
  getGeographic: async (): Promise<GeographicBreakdownResponse> => {
    const response = await apiClient.get('/portfolio/geographic')
    return handleResponse(response)
  },

  // Get score distribution
  getScores: async (): Promise<ScoreDistributionResponse> => {
    const response = await apiClient.get('/portfolio/scores')
    return handleResponse(response)
  },

  // Get risk analysis
  getRisk: async (): Promise<RiskAnalysisResponse> => {
    const response = await apiClient.get('/portfolio/risk')
    return handleResponse(response)
  },

  // Get performance tracking
  getPerformance: async (): Promise<PerformanceTrackingResponse> => {
    const response = await apiClient.get('/portfolio/performance')
    return handleResponse(response)
  },

  // Get full export (all analytics combined)
  getExport: async (): Promise<PortfolioAnalyticsExport> => {
    const response = await apiClient.get('/portfolio/export')
    return handleResponse(response)
  },
}

// Auth response types
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// Authentication API (for future use)
export const authApi = {
  // Login
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post('/auth/login', { email, password })
    return handleResponse(response)
  },

  // Logout
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout')
    localStorage.removeItem('auth_token')
  },

  // Refresh token
  refreshToken: async (): Promise<{ access_token: string; expires_in: number }> => {
    const response = await apiClient.post('/auth/refresh')
    return handleResponse(response)
  },
}

// Default export with all APIs
export const api = {
  properties: propertiesApi,
  counties: countiesApi,
  ai: aiApi,
  import: importApi,
  export: exportApi,
  user: userApi,
  applications: applicationApi,
  watchlist: watchlistApi,
  sync: syncApi,
  system: systemApi,
  auth: authApi,
  portfolio: portfolioApi,
}

export default api

// Utility functions
export const isApiError = (error: unknown): error is APIError => {
  return error !== null && typeof error === 'object' && 'name' in error && (error as { name: string }).name === 'APIError'
}

export const getApiErrorMessage = (error: unknown): string => {
  if (isApiError(error)) {
    return error.details?.message || error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}

// Export AuthManager and ConnectionManager for debugging and manual management
export { AuthManager, ConnectionManager }

// Auth status type
export interface AuthStatusInfo {
  hasToken: boolean
  isExpired: boolean
  expiresAt: string | null
  deviceId: string
}

// Authentication utility functions
export const getAuthStatus = (): AuthStatusInfo => {
  return AuthManager.getAuthStatus()
}

export const clearAuthentication = (): void => {
  AuthManager.clearAuth()
}

export const forceTokenRefresh = async (): Promise<string> => {
  AuthManager.clearAuth()
  return await AuthManager.ensureValidToken()
}

// Connection utilities
export const checkApiConnection = async (): Promise<boolean> => {
  try {
    await systemApi.getHealth()
    ConnectionManager.setOnline(true)
    return true
  } catch (error) {
    console.error('API connection check failed:', error)
    ConnectionManager.setOnline(false)
    return false
  }
}

export const waitForApi = async (timeout = 30000): Promise<boolean> => {
  const start = Date.now()

  while (Date.now() - start < timeout) {
    if (await checkApiConnection()) {
      ConnectionManager.setOnline(true)
      return true
    }

    // Wait 1 second before trying again
    await new Promise(resolve => setTimeout(resolve, 1000))
  }

  return false
}

// Connection status utilities
export const getConnectionStatus = (): boolean => {
  return ConnectionManager.getStatus()
}

export const subscribeToConnectionStatus = (callback: (online: boolean) => void): () => void => {
  return ConnectionManager.subscribe(callback)
}