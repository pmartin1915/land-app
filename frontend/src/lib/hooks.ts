// React hooks for API integration using TanStack Query

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import {
  Property,
  County,
  AISuggestion,
  PropertyFilters,
  SearchParams,
  PaginatedResponse,
} from '../types'

// Query key factories for consistent cache key management
const queryKeys = {
  properties: {
    all: ['properties'] as const,
    list: (params?: SearchParams) => ['properties', 'list', params] as const,
    detail: (id: string) => ['properties', 'detail', id] as const,
    stats: (filters?: PropertyFilters) => ['properties', 'stats', filters] as const,
    workflow: ['properties', 'workflow'] as const,
    map: (filters?: PropertyFilters, minScore?: number) => ['properties', 'map', filters, minScore] as const,
    search: (query: string, filters?: PropertyFilters) => ['properties', 'search', query, filters] as const,
    topPicks: (params: Record<string, unknown>) => ['properties', 'top-picks', params] as const,
  },
  counties: {
    all: ['counties'] as const,
    list: ['counties', 'list'] as const,
    stats: (code?: string) => ['counties', 'stats', code] as const,
  },
  ai: {
    suggestions: (propertyId: string) => ['ai', 'suggestions', propertyId] as const,
    triage: ['ai', 'triage'] as const,
  },
  portfolio: {
    all: ['portfolio'] as const,
    summary: ['portfolio', 'summary'] as const,
    geographic: ['portfolio', 'geographic'] as const,
    scores: ['portfolio', 'scores'] as const,
    risk: ['portfolio', 'risk'] as const,
    performance: ['portfolio', 'performance'] as const,
  },
}

// Properties hooks
export function useProperties(params?: SearchParams) {
  const paramsKey = useMemo(() => params, [JSON.stringify(params)])

  const result = useQuery({
    queryKey: queryKeys.properties.list(paramsKey),
    queryFn: () => api.properties.getProperties(params),
    staleTime: 5 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function useProperty(id: string) {
  const result = useQuery({
    queryKey: queryKeys.properties.detail(id),
    queryFn: () => api.properties.getProperty(id),
    staleTime: 10 * 60 * 1000,
    enabled: !!id,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function usePropertyStats(filters?: PropertyFilters) {
  const filtersKey = useMemo(() => filters, [JSON.stringify(filters)])

  const result = useQuery({
    queryKey: queryKeys.properties.stats(filtersKey),
    queryFn: () => api.properties.getPropertyStats(filters),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function useWorkflowStats() {
  const result = useQuery({
    queryKey: queryKeys.properties.workflow,
    queryFn: () => api.properties.getWorkflowStats(),
    staleTime: 1 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function useMapProperties(filters?: PropertyFilters, minScore?: number) {
  const filtersKey = useMemo(() => filters, [JSON.stringify(filters)])

  const result = useQuery({
    queryKey: queryKeys.properties.map(filtersKey, minScore),
    queryFn: async () => {
      const params: SearchParams = {
        page: 1,
        per_page: 1000,
        sort_by: 'investment_score',
        sort_order: 'desc',
        filters: {
          ...filters,
          min_investment_score: minScore,
        }
      }
      const response = await api.properties.getProperties(params)
      return response.items
    },
    staleTime: 5 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

// Search hook with debouncing
export function usePropertySearch(query: string, filters?: PropertyFilters, debounceMs = 300) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)
  const [isSearching, setIsSearching] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, debounceMs)
    return () => clearTimeout(timer)
  }, [query, debounceMs])

  const filtersKey = useMemo(() => filters, [JSON.stringify(filters)])

  const result = useQuery({
    queryKey: queryKeys.properties.search(debouncedQuery, filtersKey),
    queryFn: () => api.properties.searchProperties(debouncedQuery, filters),
    staleTime: 3 * 60 * 1000,
    enabled: debouncedQuery.length > 2,
  })

  useEffect(() => {
    setIsSearching(query !== debouncedQuery)
  }, [query, debouncedQuery])

  return {
    data: result.data ?? [],
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isSearching,
    query: debouncedQuery,
  }
}

// Counties hooks
export function useCounties() {
  const result = useQuery({
    queryKey: queryKeys.counties.list,
    queryFn: () => api.counties.getCounties(),
    staleTime: 60 * 60 * 1000, // 1 hour
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function useCountyStats(code?: string) {
  const result = useQuery({
    queryKey: queryKeys.counties.stats(code),
    queryFn: () => api.counties.getCountyStats(code),
    staleTime: 10 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

// AI Suggestions hooks
export function usePropertySuggestions(propertyId: string) {
  const result = useQuery({
    queryKey: queryKeys.ai.suggestions(propertyId),
    queryFn: () => api.ai.getPropertySuggestions(propertyId),
    staleTime: 2 * 60 * 1000,
    enabled: !!propertyId,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function useTriageQueue() {
  const result = useQuery({
    queryKey: queryKeys.ai.triage,
    queryFn: () => api.ai.getTriageQueue(),
    staleTime: 1 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

// Mutation hooks
export function usePropertyMutations() {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<Property> }) =>
      api.properties.updateProperty(id, updates),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.all })
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.detail(variables.id) })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const createMutation = useMutation({
    mutationFn: (property: Partial<Property>) => api.properties.createProperty(property),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.all })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.properties.deleteProperty(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.all })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const updateProperty = useCallback(async (id: string, updates: Partial<Property>) => {
    return updateMutation.mutateAsync({ id, updates })
  }, [updateMutation])

  const createProperty = useCallback(async (property: Partial<Property>) => {
    return createMutation.mutateAsync(property)
  }, [createMutation])

  const deleteProperty = useCallback(async (id: string) => {
    return deleteMutation.mutateAsync(id)
  }, [deleteMutation])

  return {
    updateProperty,
    createProperty,
    deleteProperty,
    loading: updateMutation.isPending || createMutation.isPending || deleteMutation.isPending,
    error,
  }
}

export function useAISuggestionMutations() {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const applyMutation = useMutation({
    mutationFn: (suggestionId: string) => api.ai.applySuggestion(suggestionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.all })
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.triage })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      api.ai.rejectSuggestion(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.triage })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const bulkApplyMutation = useMutation({
    mutationFn: (ids: string[]) => api.ai.bulkApplySuggestions(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.properties.all })
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.triage })
      setError(null)
    },
    onError: (err: Error) => setError(err.message),
  })

  const applySuggestion = useCallback(async (suggestionId: string) => {
    return applyMutation.mutateAsync(suggestionId)
  }, [applyMutation])

  const rejectSuggestion = useCallback(async (suggestionId: string, reason?: string) => {
    return rejectMutation.mutateAsync({ id: suggestionId, reason })
  }, [rejectMutation])

  const bulkApplySuggestions = useCallback(async (suggestionIds: string[]) => {
    return bulkApplyMutation.mutateAsync(suggestionIds)
  }, [bulkApplyMutation])

  return {
    applySuggestion,
    rejectSuggestion,
    bulkApplySuggestions,
    loading: applyMutation.isPending || rejectMutation.isPending || bulkApplyMutation.isPending,
    error,
  }
}

// API health monitoring hook
export function useApiHealth() {
  const [isConnected, setIsConnected] = useState(true)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const checkHealth = useCallback(async () => {
    try {
      await api.system.getHealth()
      setIsConnected(true)
      setLastCheck(new Date())
    } catch {
      setIsConnected(false)
      setLastCheck(new Date())
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30 * 1000)
    return () => clearInterval(interval)
  }, [checkHealth])

  return { isConnected, lastCheck, checkHealth }
}

// Top Picks hook for beginner-friendly properties
export function useTopPicks(params: {
  state?: string
  maxEffectiveCost?: number
  limit?: number
} = {}) {
  const { state = 'AR', maxEffectiveCost = 8000, limit = 5 } = params

  const searchParams: SearchParams = useMemo(() => ({
    filters: { state, maxEffectiveCost },
    sort_by: 'buy_hold_score',
    sort_order: 'desc' as const,
    per_page: limit,
    page: 1,
  }), [state, maxEffectiveCost, limit])

  const result = useQuery({
    queryKey: queryKeys.properties.topPicks({ state, maxEffectiveCost, limit }),
    queryFn: () => api.properties.getProperties(searchParams),
    staleTime: 5 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

// Local storage hook for user preferences
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch {
      return initialValue
    }
  })

  const setStoredValue = useCallback((newValue: T | ((val: T) => T)) => {
    try {
      const valueToStore = newValue instanceof Function ? newValue(value) : newValue
      setValue(valueToStore)
      localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error)
    }
  }, [key, value])

  return [value, setStoredValue] as const
}

// Portfolio Analytics hooks
import {
  PortfolioSummaryResponse,
  GeographicBreakdownResponse,
  ScoreDistributionResponse,
  RiskAnalysisResponse,
  PerformanceTrackingResponse,
} from '../types/portfolio'

export function usePortfolioSummary() {
  const result = useQuery({
    queryKey: queryKeys.portfolio.summary,
    queryFn: () => api.portfolio.getSummary(),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function usePortfolioGeographic() {
  const result = useQuery({
    queryKey: queryKeys.portfolio.geographic,
    queryFn: () => api.portfolio.getGeographic(),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function usePortfolioScores() {
  const result = useQuery({
    queryKey: queryKeys.portfolio.scores,
    queryFn: () => api.portfolio.getScores(),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function usePortfolioRisk() {
  const result = useQuery({
    queryKey: queryKeys.portfolio.risk,
    queryFn: () => api.portfolio.getRisk(),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

export function usePortfolioPerformance() {
  const result = useQuery({
    queryKey: queryKeys.portfolio.performance,
    queryFn: () => api.portfolio.getPerformance(),
    staleTime: 2 * 60 * 1000,
  })

  return {
    data: result.data ?? null,
    loading: result.isLoading ? 'loading' : result.isSuccess ? 'succeeded' : result.isError ? 'failed' : 'idle',
    error: result.error?.message ?? null,
    refetch: result.refetch,
    isLoading: result.isLoading,
    isSuccess: result.isSuccess,
    isError: result.isError,
    isStale: result.isStale,
    lastFetchTime: result.dataUpdatedAt ? new Date(result.dataUpdatedAt) : null,
  }
}

// Export query keys for use in cache invalidation from api.ts
export { queryKeys }
