// React hooks for API integration with caching and state management

import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from './api'
import { propertyCache, globalCache, createCacheKey } from './cache'
import {
  Property,
  County,
  AISuggestion,
  PropertyFilters,
  SearchParams,
  PaginatedResponse,
  LoadingState,
} from '../types'

// Generic async data hook
export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  dependencies: any[] = [],
  options: {
    cacheKey?: string
    cacheTTL?: number
    enabled?: boolean
  } = {}
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState<LoadingState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [initialFetchDone, setInitialFetchDone] = useState(false)

  const { cacheKey, cacheTTL, enabled = true } = options

  const fetchData = useCallback(async (isRefetch = false) => {
    if (!enabled) return

    // Only show loading on initial fetch or explicit refetch, not on cache hits
    if (isRefetch) {
      setLoading('loading')
    }
    setError(null)

    try {
      let result: T

      if (cacheKey) {
        // Try cache first (only on initial fetch, not refetch)
        if (!isRefetch) {
          const cached = await globalCache.get<T>(cacheKey)
          if (cached) {
            setData(cached)
            setLoading('succeeded')
            setInitialFetchDone(true)
            return
          }
          // No cache hit, now show loading
          setLoading('loading')
        }

        // Fetch and cache
        result = await fetcher()
        await globalCache.set(cacheKey, result, cacheTTL)
      } else {
        setLoading('loading')
        result = await fetcher()
      }

      setData(result)
      setLoading('succeeded')
      setInitialFetchDone(true)
    } catch (err: any) {
      setError(err.message || 'An error occurred')
      setLoading('failed')
    }
  }, [fetcher, cacheKey, cacheTTL, enabled, ...dependencies])

  useEffect(() => {
    fetchData(false)
  }, [fetchData])

  const refetch = useCallback(() => {
    if (cacheKey) {
      globalCache.remove(cacheKey)
    }
    fetchData(true)
  }, [fetchData, cacheKey])

  return {
    data,
    loading,
    error,
    refetch,
    isLoading: loading === 'loading',
    isSuccess: loading === 'succeeded',
    isError: loading === 'failed',
  }
}

// Properties hooks
export function useProperties(params?: SearchParams) {
  const cacheKey = useMemo(() =>
    createCacheKey('properties', params),
    [params]
  )

  // Memoize stringified params to prevent unnecessary refetches
  const stringifiedParams = useMemo(() => JSON.stringify(params), [params])

  return useAsyncData<PaginatedResponse<Property>>(
    () => api.properties.getProperties(params),
    [stringifiedParams],
    {
      cacheKey,
      cacheTTL: 5 * 60 * 1000, // 5 minutes
    }
  )
}

export function useProperty(id: string) {
  const cacheKey = useMemo(() =>
    createCacheKey('property', { id }),
    [id]
  )

  return useAsyncData<Property>(
    () => api.properties.getProperty(id),
    [id],
    {
      cacheKey,
      cacheTTL: 10 * 60 * 1000, // 10 minutes
      enabled: !!id,
    }
  )
}

export function usePropertyStats(filters?: PropertyFilters) {
  const cacheKey = useMemo(() =>
    createCacheKey('property-stats', filters),
    [filters]
  )

  // Memoize stringified filters to prevent unnecessary refetches
  const stringifiedFilters = useMemo(() => JSON.stringify(filters), [filters])

  return useAsyncData(
    () => api.properties.getPropertyStats(filters),
    [stringifiedFilters],
    {
      cacheKey,
      cacheTTL: 2 * 60 * 1000, // 2 minutes
    }
  )
}

// Hook for fetching workflow statistics (property counts by status)
export function useWorkflowStats() {
  const cacheKey = 'workflow-stats'

  return useAsyncData<{
    new: number
    reviewing: number
    bid_ready: number
    rejected: number
    purchased: number
    total: number
  }>(
    () => api.properties.getWorkflowStats(),
    [],
    {
      cacheKey,
      cacheTTL: 1 * 60 * 1000, // 1 minute (workflow changes frequently)
    }
  )
}

// Hook for fetching all properties for map view (up to 1000)
export function useMapProperties(filters?: PropertyFilters, minScore?: number) {
  const cacheKey = useMemo(() =>
    createCacheKey('map-properties', { filters, minScore }),
    [filters, minScore]
  )

  return useAsyncData<Property[]>(
    async () => {
      // Fetch properties with high page_size for map view
      const params: SearchParams = {
        page: 1,
        per_page: 1000, // Max allowed by API
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
    [JSON.stringify(filters), minScore],
    {
      cacheKey,
      cacheTTL: 5 * 60 * 1000, // 5 minutes
    }
  )
}

// Search hook with debouncing
export function usePropertySearch(query: string, filters?: PropertyFilters, debounceMs = 300) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)
  const [isSearching, setIsSearching] = useState(false)

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [query, debounceMs])

  const cacheKey = useMemo(() =>
    createCacheKey('property-search', { query: debouncedQuery, filters }),
    [debouncedQuery, filters]
  )

  const { data, loading, error, refetch } = useAsyncData<Property[]>(
    () => api.properties.searchProperties(debouncedQuery, filters),
    [debouncedQuery, JSON.stringify(filters)],
    {
      cacheKey,
      cacheTTL: 3 * 60 * 1000, // 3 minutes
      enabled: debouncedQuery.length > 2, // Only search if query is long enough
    }
  )

  // Track searching state separately from loading
  useEffect(() => {
    if (query !== debouncedQuery) {
      setIsSearching(true)
    } else {
      setIsSearching(false)
    }
  }, [query, debouncedQuery])

  return {
    data: data || [],
    loading,
    error,
    refetch,
    isSearching,
    query: debouncedQuery,
  }
}

// Counties hook
export function useCounties() {
  const cacheKey = 'counties'

  return useAsyncData<County[]>(
    () => api.counties.getCounties(),
    [],
    {
      cacheKey,
      cacheTTL: 60 * 60 * 1000, // 1 hour (counties don't change often)
    }
  )
}

export function useCountyStats(code?: string) {
  const cacheKey = useMemo(() =>
    createCacheKey('county-stats', { code }),
    [code]
  )

  return useAsyncData(
    () => api.counties.getCountyStats(code),
    [code],
    {
      cacheKey,
      cacheTTL: 10 * 60 * 1000, // 10 minutes
    }
  )
}

// AI Suggestions hooks
export function usePropertySuggestions(propertyId: string) {
  const cacheKey = useMemo(() =>
    createCacheKey('property-suggestions', { propertyId }),
    [propertyId]
  )

  return useAsyncData<AISuggestion[]>(
    () => api.ai.getPropertySuggestions(propertyId),
    [propertyId],
    {
      cacheKey,
      cacheTTL: 2 * 60 * 1000, // 2 minutes
      enabled: !!propertyId,
    }
  )
}

export function useTriageQueue() {
  const cacheKey = 'triage-queue'

  return useAsyncData<AISuggestion[]>(
    () => api.ai.getTriageQueue(),
    [],
    {
      cacheKey,
      cacheTTL: 1 * 60 * 1000, // 1 minute (triage changes frequently)
    }
  )
}

// Mutation hooks for data updates
export function usePropertyMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateProperty = useCallback(async (id: string, updates: Partial<Property>) => {
    setLoading(true)
    setError(null)

    try {
      const updated = await api.properties.updateProperty(id, updates)

      // Invalidate related cache entries
      await propertyCache.invalidateByTags(['properties'])
      await globalCache.remove(createCacheKey('property', { id }))

      setLoading(false)
      return updated
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  const createProperty = useCallback(async (property: Partial<Property>) => {
    setLoading(true)
    setError(null)

    try {
      const created = await api.properties.createProperty(property)

      // Invalidate properties cache
      await propertyCache.invalidateByTags(['properties'])

      setLoading(false)
      return created
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  const deleteProperty = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)

    try {
      await api.properties.deleteProperty(id)

      // Invalidate related cache entries
      await propertyCache.invalidateByTags(['properties'])
      await globalCache.remove(createCacheKey('property', { id }))

      setLoading(false)
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  return {
    updateProperty,
    createProperty,
    deleteProperty,
    loading,
    error,
  }
}

export function useAISuggestionMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const applySuggestion = useCallback(async (suggestionId: string) => {
    setLoading(true)
    setError(null)

    try {
      const result = await api.ai.applySuggestion(suggestionId)

      // Invalidate related caches
      await propertyCache.invalidateByTags(['properties', 'suggestions'])
      await globalCache.remove('triage-queue')

      setLoading(false)
      return result
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  const rejectSuggestion = useCallback(async (suggestionId: string, reason?: string) => {
    setLoading(true)
    setError(null)

    try {
      await api.ai.rejectSuggestion(suggestionId, reason)

      // Invalidate triage queue
      await globalCache.remove('triage-queue')

      setLoading(false)
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  const bulkApplySuggestions = useCallback(async (suggestionIds: string[]) => {
    setLoading(true)
    setError(null)

    try {
      const results = await api.ai.bulkApplySuggestions(suggestionIds)

      // Invalidate related caches
      await propertyCache.invalidateByTags(['properties', 'suggestions'])
      await globalCache.remove('triage-queue')

      setLoading(false)
      return results
    } catch (err: any) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [])

  return {
    applySuggestion,
    rejectSuggestion,
    bulkApplySuggestions,
    loading,
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
    } catch (error) {
      setIsConnected(false)
      setLastCheck(new Date())
    }
  }, [])

  // Check health every 30 seconds
  useEffect(() => {
    checkHealth()

    const interval = setInterval(checkHealth, 30 * 1000)
    return () => clearInterval(interval)
  }, [checkHealth])

  return {
    isConnected,
    lastCheck,
    checkHealth,
  }
}

// Local storage hook for user preferences
export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error)
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