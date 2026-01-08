import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom'
import { PropertyFilters, SortOrder } from '../types'

interface UrlTableState {
  // Sorting
  sortBy?: string
  sortOrder?: SortOrder
  // Pagination
  page: number
  perPage: number
  // Search
  query?: string
  // Filters
  filters: PropertyFilters
}

interface UseUrlStateOptions {
  defaultPerPage?: number
  debounceMs?: number
}

const DEFAULT_PER_PAGE = 25
const DEBOUNCE_MS = 300

// Parse URL params into state
function parseUrlParams(searchParams: URLSearchParams): UrlTableState {
  const state: UrlTableState = {
    page: 1,
    perPage: DEFAULT_PER_PAGE,
    filters: {}
  }

  // Sorting
  const sort = searchParams.get('sort')
  const order = searchParams.get('order')
  if (sort) {
    state.sortBy = sort
    state.sortOrder = (order === 'asc' || order === 'desc') ? order : 'desc'
  }

  // Pagination
  const page = searchParams.get('page')
  const perPage = searchParams.get('per_page')
  if (page) {
    state.page = Math.max(1, parseInt(page, 10) || 1)
  }
  if (perPage) {
    state.perPage = Math.max(10, Math.min(100, parseInt(perPage, 10) || DEFAULT_PER_PAGE))
  }

  // Search query
  const query = searchParams.get('q')
  if (query) {
    state.query = query
  }

  // Filters
  const filters: PropertyFilters = {}

  // State filter
  const stateFilter = searchParams.get('state')
  if (stateFilter) {
    filters.state = stateFilter
  }

  // County filter
  const county = searchParams.get('county')
  if (county) {
    filters.county = county
  }

  // Price range
  const minPrice = searchParams.get('minPrice')
  const maxPrice = searchParams.get('maxPrice')
  if (minPrice || maxPrice) {
    filters.priceRange = [
      minPrice ? parseInt(minPrice, 10) : 0,
      maxPrice ? parseInt(maxPrice, 10) : 100000
    ]
  }

  // Acreage range
  const minAcreage = searchParams.get('minAcreage')
  const maxAcreage = searchParams.get('maxAcreage')
  if (minAcreage || maxAcreage) {
    filters.acreageRange = [
      minAcreage ? parseFloat(minAcreage) : 0,
      maxAcreage ? parseFloat(maxAcreage) : 100
    ]
  }

  // Score filters
  const minScore = searchParams.get('minScore')
  if (minScore) {
    filters.minInvestmentScore = parseInt(minScore, 10)
  }

  const minCountyScore = searchParams.get('minCountyScore')
  if (minCountyScore) {
    filters.minCountyMarketScore = parseInt(minCountyScore, 10)
  }

  const minGeoScore = searchParams.get('minGeoScore')
  if (minGeoScore) {
    filters.minGeographicScore = parseInt(minGeoScore, 10)
  }

  // Boolean filters
  if (searchParams.get('waterOnly') === 'true') {
    filters.waterOnly = true
  }

  if (searchParams.get('excludeDelta') === 'true') {
    filters.excludeDeltaRegion = true
  }

  // Year filter
  const minYear = searchParams.get('minYear')
  if (minYear) {
    filters.minYearSold = parseInt(minYear, 10)
  }

  // Period filter
  const period = searchParams.get('period')
  if (period) {
    const now = new Date()
    let createdAfter: string | undefined

    switch (period) {
      case 'last-24-hours':
        createdAfter = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
        break
      case 'last-7-days':
        createdAfter = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()
        break
      case 'last-30-days':
        createdAfter = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString()
        break
      case 'last-quarter':
        createdAfter = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString()
        break
      case 'last-year':
        createdAfter = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000).toISOString()
        break
    }

    if (createdAfter) {
      filters.createdAfter = createdAfter
    }
  }

  state.filters = filters

  return state
}

// Convert state to URL params
function stateToUrlParams(state: UrlTableState): URLSearchParams {
  const params = new URLSearchParams()

  // Sorting
  if (state.sortBy) {
    params.set('sort', state.sortBy)
    params.set('order', state.sortOrder || 'desc')
  }

  // Pagination (only if not default)
  if (state.page > 1) {
    params.set('page', state.page.toString())
  }
  if (state.perPage !== DEFAULT_PER_PAGE) {
    params.set('per_page', state.perPage.toString())
  }

  // Search query
  if (state.query) {
    params.set('q', state.query)
  }

  // Filters
  const { filters } = state

  if (filters.state) {
    params.set('state', filters.state)
  }

  if (filters.county) {
    params.set('county', filters.county)
  }

  if (filters.priceRange) {
    if (filters.priceRange[0] > 0) {
      params.set('minPrice', filters.priceRange[0].toString())
    }
    if (filters.priceRange[1] < 100000) {
      params.set('maxPrice', filters.priceRange[1].toString())
    }
  }

  if (filters.acreageRange) {
    if (filters.acreageRange[0] > 0) {
      params.set('minAcreage', filters.acreageRange[0].toString())
    }
    if (filters.acreageRange[1] < 100) {
      params.set('maxAcreage', filters.acreageRange[1].toString())
    }
  }

  if (filters.minInvestmentScore) {
    params.set('minScore', filters.minInvestmentScore.toString())
  }

  if (filters.minCountyMarketScore) {
    params.set('minCountyScore', filters.minCountyMarketScore.toString())
  }

  if (filters.minGeographicScore) {
    params.set('minGeoScore', filters.minGeographicScore.toString())
  }

  if (filters.waterOnly) {
    params.set('waterOnly', 'true')
  }

  if (filters.excludeDeltaRegion) {
    params.set('excludeDelta', 'true')
  }

  if (filters.minYearSold) {
    params.set('minYear', filters.minYearSold.toString())
  }

  return params
}

export function useUrlState(options: UseUrlStateOptions = {}) {
  const { defaultPerPage = DEFAULT_PER_PAGE, debounceMs = DEBOUNCE_MS } = options

  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()

  // Parse initial state from URL
  const initialState = useMemo(() => {
    const parsed = parseUrlParams(searchParams)
    if (parsed.perPage === DEFAULT_PER_PAGE && defaultPerPage !== DEFAULT_PER_PAGE) {
      parsed.perPage = defaultPerPage
    }
    return parsed
  }, []) // Only parse on mount

  // Local state for immediate UI updates
  const [localState, setLocalState] = useState<UrlTableState>(initialState)

  // Ref to track programmatic URL updates (prevents infinite loop)
  const isUpdatingUrl = useRef(false)
  // Ref to store debounce timer for cancellation on navigation
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced URL update
  useEffect(() => {
    // Clear any existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      const newParams = stateToUrlParams(localState)
      const currentParams = searchParams.toString()
      const newParamsString = newParams.toString()

      // Only update if params actually changed
      if (currentParams !== newParamsString) {
        isUpdatingUrl.current = true
        setSearchParams(newParams, { replace: true })
      }
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [localState, debounceMs, setSearchParams])

  // Sync from URL changes (e.g., browser back/forward)
  useEffect(() => {
    // Skip if we just updated the URL ourselves (prevents infinite loop)
    if (isUpdatingUrl.current) {
      isUpdatingUrl.current = false
      return
    }
    // Cancel any pending debounced updates to prevent overwriting navigation
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    const urlState = parseUrlParams(searchParams)
    setLocalState(urlState)
  }, [searchParams])

  // Update functions
  const setSorting = useCallback((sortBy?: string, sortOrder?: SortOrder) => {
    setLocalState(prev => ({
      ...prev,
      sortBy,
      sortOrder,
      page: 1 // Reset to first page on sort change
    }))
  }, [])

  const setPage = useCallback((page: number) => {
    setLocalState(prev => ({
      ...prev,
      page
    }))
  }, [])

  const setPerPage = useCallback((perPage: number) => {
    setLocalState(prev => ({
      ...prev,
      perPage,
      page: 1 // Reset to first page
    }))
  }, [])

  const setQuery = useCallback((query?: string) => {
    setLocalState(prev => ({
      ...prev,
      query,
      page: 1 // Reset to first page on search
    }))
  }, [])

  const setFilters = useCallback((filters: PropertyFilters) => {
    setLocalState(prev => ({
      ...prev,
      filters,
      page: 1 // Reset to first page on filter change
    }))
  }, [])

  const updateFilter = useCallback(<K extends keyof PropertyFilters>(
    key: K,
    value: PropertyFilters[K]
  ) => {
    setLocalState(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [key]: value
      },
      page: 1
    }))
  }, [])

  const resetFilters = useCallback(() => {
    setLocalState(prev => ({
      ...prev,
      filters: {},
      page: 1
    }))
  }, [])

  const resetAll = useCallback(() => {
    setLocalState({
      page: 1,
      perPage: defaultPerPage,
      filters: {}
    })
  }, [defaultPerPage])

  // Generate shareable URL
  const getShareableUrl = useCallback(() => {
    const params = stateToUrlParams(localState)
    const baseUrl = window.location.origin + location.pathname
    const queryString = params.toString()
    return queryString ? `${baseUrl}?${queryString}` : baseUrl
  }, [localState, location.pathname])

  // Copy URL to clipboard
  const copyUrlToClipboard = useCallback(async () => {
    const url = getShareableUrl()
    try {
      await navigator.clipboard.writeText(url)
      return true
    } catch (err) {
      console.error('Failed to copy URL:', err)
      return false
    }
  }, [getShareableUrl])

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    const { filters, query } = localState
    return !!(
      query ||
      filters.state ||
      filters.county ||
      filters.priceRange ||
      filters.acreageRange ||
      filters.minInvestmentScore ||
      filters.minCountyMarketScore ||
      filters.minGeographicScore ||
      filters.waterOnly ||
      filters.excludeDeltaRegion ||
      filters.minYearSold ||
      filters.createdAfter
    )
  }, [localState])

  // Count active filters
  const activeFilterCount = useMemo(() => {
    const { filters } = localState
    let count = 0
    if (filters.state) count++
    if (filters.county) count++
    if (filters.priceRange) count++
    if (filters.acreageRange) count++
    if (filters.minInvestmentScore) count++
    if (filters.minCountyMarketScore) count++
    if (filters.minGeographicScore) count++
    if (filters.waterOnly) count++
    if (filters.excludeDeltaRegion) count++
    if (filters.minYearSold) count++
    if (filters.createdAfter) count++
    return count
  }, [localState])

  return {
    // State
    sortBy: localState.sortBy,
    sortOrder: localState.sortOrder,
    page: localState.page,
    perPage: localState.perPage,
    query: localState.query,
    filters: localState.filters,

    // Setters
    setSorting,
    setPage,
    setPerPage,
    setQuery,
    setFilters,
    updateFilter,
    resetFilters,
    resetAll,

    // Helpers
    hasActiveFilters,
    activeFilterCount,
    getShareableUrl,
    copyUrlToClipboard,
  }
}

// Simplified hook for just filters (for TopBar)
export function useUrlFilters() {
  const { filters, setFilters, updateFilter, resetFilters, hasActiveFilters, activeFilterCount } = useUrlState()

  return {
    filters,
    setFilters,
    updateFilter,
    resetFilters,
    hasActiveFilters,
    activeFilterCount,
  }
}
