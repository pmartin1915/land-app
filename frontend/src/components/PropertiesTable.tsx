import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  RowSelectionState,
  PaginationState,
  Updater,
} from '@tanstack/react-table'
import {
  ChevronUp,
  ChevronDown,
  Eye,
  EyeOff,
  Download,
  Star,
  MapPin,
  Share2,
  Loader2,
  AlertTriangle,
  GitCompare
} from 'lucide-react'
import { Property, PropertyFilters, SearchParams } from '../types'
import { api } from '../lib/api'
import { useProperties } from '../lib/hooks'
import { useUrlState } from '../lib/useUrlState'
import { TableSkeleton } from './ui/LoadingSkeleton'
import { ErrorState } from './ui/ErrorState'
import { EmptyState, FilterEmptyState } from './ui/EmptyState'
import { showToast } from './ui/Toast'
import { InvestmentGradeBadge } from './ui/InvestmentGradeBadge'
import { ScoreTooltip } from './ui/ScoreTooltip'
import { usePropertyCompare } from './PropertyCompareContext'
import { useConnectionStatus } from './ui/ConnectionStatus'

interface PropertiesTableProps {
  onRowSelect?: (property: Property | null) => void
  globalFilters?: PropertyFilters
  searchQuery?: string
}

// Watchlist status cache
interface WatchlistStatus {
  [propertyId: string]: boolean
}

// Memoized ActionsCell component to prevent column recreation on watchlist state changes
interface ActionsCellProps {
  property: Property
  isWatched: boolean
  isToggling: boolean
  onView: ((property: Property) => void) | undefined
  onToggleWatch: (propertyId: string, e: React.MouseEvent) => void
}

const ActionsCell = React.memo(function ActionsCell({
  property,
  isWatched,
  isToggling,
  onView,
  onToggleWatch
}: ActionsCellProps) {
  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={() => onView?.(property)}
        className="p-1 hover:bg-surface rounded transition-colors"
        title="View Details"
        aria-label="View property details"
      >
        <Eye className="w-4 h-4" />
      </button>
      <button
        onClick={(e) => onToggleWatch(property.id, e)}
        disabled={isToggling}
        className={`p-1 rounded transition-colors ${
          isWatched
            ? 'text-warning hover:text-warning/80'
            : 'text-text-muted hover:text-warning'
        } ${isToggling ? 'opacity-50' : ''}`}
        title={isWatched ? 'Remove from Watchlist' : 'Add to Watchlist'}
        aria-label={isWatched ? 'Remove from watchlist' : 'Add to watchlist'}
      >
        {isToggling ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Star className={`w-4 h-4 ${isWatched ? 'fill-warning' : ''}`} />
        )}
      </button>
      <button
        className="p-1 hover:bg-surface rounded transition-colors"
        title="View on Map"
        aria-label="View property on map"
      >
        <MapPin className="w-4 h-4" />
      </button>
    </div>
  )
})

// Memoized CompareCell component for comparison toggle
interface CompareCellProps {
  property: Property
  isInCompare: boolean
  isAtLimit: boolean
  onToggleCompare: (property: Property) => void
}

const CompareCell = React.memo(function CompareCell({
  property,
  isInCompare,
  isAtLimit,
  onToggleCompare
}: CompareCellProps) {
  const isDisabled = !isInCompare && isAtLimit

  return (
    <input
      type="checkbox"
      checked={isInCompare}
      disabled={isDisabled}
      onChange={() => onToggleCompare(property)}
      className={`w-4 h-4 text-accent-secondary border-neutral-1 rounded focus:ring-accent-secondary ${
        isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      }`}
      title={isDisabled ? 'Maximum 3 properties for comparison' : isInCompare ? 'Remove from comparison' : 'Add to comparison'}
      aria-label={isDisabled ? 'Maximum 3 properties for comparison' : isInCompare ? 'Remove from comparison' : 'Add to comparison'}
    />
  )
})

export function PropertiesTable({ onRowSelect, globalFilters, searchQuery }: PropertiesTableProps) {
  // URL state for shareable links
  const {
    sortBy,
    sortOrder,
    page,
    perPage,
    setPage,
    setPerPage,
    setSorting,
    activeFilterCount,
    resetFilters,
    copyUrlToClipboard
  } = useUrlState({ defaultPerPage: 25 })

  // Property comparison context
  const {
    toggleCompare,
    isInCompare,
    isAtLimit,
    compareCount,
    setShowCompareModal,
    clearCompare
  } = usePropertyCompare()

  // Connection status for banner space calculation
  const isOnline = useConnectionStatus()
  // Reserve bottom padding when any fixed banner might be visible
  const hasBanners = compareCount > 0 || !isOnline

  // Table state - derived from URL state (single source of truth)
  // Sorting and pagination are derived, not stored locally, to prevent sync loops
  const sorting: SortingState = useMemo(() =>
    sortBy ? [{ id: sortBy, desc: sortOrder === 'desc' }] : [],
    [sortBy, sortOrder]
  )

  const pagination: PaginationState = useMemo(() => ({
    pageIndex: page - 1,
    pageSize: perPage,
  }), [page, perPage])

  // Local state for table features that don't need URL persistence
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})

  // Watchlist state
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>({})
  const [togglingWatch, setTogglingWatch] = useState<Set<string>>(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  // Refs to track current state for callbacks (avoids stale closures and prevents re-renders)
  const watchlistStatusRef = useRef(watchlistStatus)
  useEffect(() => {
    watchlistStatusRef.current = watchlistStatus
  }, [watchlistStatus])

  const togglingWatchRef = useRef(togglingWatch)
  useEffect(() => {
    togglingWatchRef.current = togglingWatch
  }, [togglingWatch])

  // Build search params for API - uses URL state directly (single source of truth)
  const searchParams: SearchParams = useMemo(() => ({
    q: searchQuery,
    filters: globalFilters,
    sort_by: sortBy,
    sort_order: sortOrder,
    page: page,
    per_page: perPage,
  }), [searchQuery, globalFilters, sortBy, sortOrder, page, perPage])

  // Fetch data
  const { data, isLoading: loading, error, refetch } = useProperties(searchParams)

  // Stabilize items reference to prevent TanStack Table re-initialization on every render
  // Use JSON stringify to only update when content changes, not just reference
  const itemsJson = JSON.stringify(data?.items || [])
  const stableItems = useMemo(() => data?.items || [],
    // eslint-disable-next-line react-hooks/exhaustive-deps -- itemsJson is stable string representation
    [itemsJson]
  )

  // Fetch watchlist status for visible properties
  const fetchWatchlistStatus = useCallback(async (propertyIds: string[]) => {
    if (propertyIds.length === 0) return

    try {
      const statusData = await api.watchlist.getBulkStatus(propertyIds)
      setWatchlistStatus(prev => ({ ...prev, ...statusData }))
    } catch (err) {
      console.error('Failed to fetch watchlist status:', err)
    }
  }, [])

  // Fetch watchlist status when data changes
  // Use stringified item IDs as dependency to prevent effect firing on reference changes
  const itemIds = useMemo(() => stableItems.map(p => p.id), [stableItems])
  const itemIdsKey = itemIds.join(',')
  useEffect(() => {
    if (itemIds.length > 0) {
      fetchWatchlistStatus(itemIds)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- itemIdsKey is stable string representation
  }, [itemIdsKey, fetchWatchlistStatus])

  // Toggle watch status for a property
  // Uses refs for state access to keep callback reference stable (prevents column recreation)
  const toggleWatch = useCallback(async (propertyId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    // Check if THIS property is already toggling (allows concurrent toggles on different properties)
    // Use ref to avoid stale closure and keep callback stable
    if (togglingWatchRef.current.has(propertyId)) return

    // Use ref for current watched status
    const wasWatched = watchlistStatusRef.current[propertyId] || false

    try {
      // Add to in-flight set
      setTogglingWatch(prev => new Set(prev).add(propertyId))
      // Optimistic update
      setWatchlistStatus(prev => ({
        ...prev,
        [propertyId]: !wasWatched
      }))

      const result = await api.watchlist.toggleWatch(propertyId)
      setWatchlistStatus(prev => ({
        ...prev,
        [propertyId]: result.is_watched
      }))
      showToast.success(
        result.is_watched ? 'Added to watchlist' : 'Removed from watchlist'
      )
    } catch (err) {
      // Revert on error
      setWatchlistStatus(prev => ({
        ...prev,
        [propertyId]: wasWatched
      }))
      showToast.error('Failed to update watchlist')
    } finally {
      // Remove from in-flight set
      setTogglingWatch(prev => {
        const next = new Set(prev)
        next.delete(propertyId)
        return next
      })
    }
  }, [])  // Empty deps - all state accessed via refs for stability

  // Handlers for table state changes - write directly to URL state
  const handleSortingChange = useCallback((updater: Updater<SortingState>) => {
    const newSorting = typeof updater === 'function' ? updater(sorting) : updater
    if (newSorting.length > 0) {
      setSorting(newSorting[0].id, newSorting[0].desc ? 'desc' : 'asc')
    } else {
      setSorting(undefined, undefined)
    }
  }, [sorting, setSorting])

  const handlePaginationChange = useCallback((updater: Updater<PaginationState>) => {
    const newPagination = typeof updater === 'function' ? updater(pagination) : updater
    setPage(newPagination.pageIndex + 1)
    setPerPage(newPagination.pageSize)
  }, [pagination, setPage, setPerPage])

  // Column definitions - memoized with stable dependencies
  const columns = useMemo<ColumnDef<Property>[]>(() => [
    // Selection column
    {
      id: 'select',
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllPageRowsSelected()}
          onChange={(e) => table.toggleAllPageRowsSelected(e.target.checked)}
          className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
          aria-label="Select all rows"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={(e) => row.toggleSelected(e.target.checked)}
          className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
          aria-label={`Select row ${row.index + 1}`}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },

    // Compare column
    {
      id: 'compare',
      header: () => (
        <div className="flex items-center gap-1" title="Compare up to 3 properties">
          <GitCompare className="w-4 h-4" />
        </div>
      ),
      cell: ({ row }) => (
        <CompareCell
          property={row.original}
          isInCompare={isInCompare(row.original.id)}
          isAtLimit={isAtLimit}
          onToggleCompare={toggleCompare}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },

    // Parcel ID
    {
      accessorKey: 'parcel_id',
      header: 'Parcel ID',
      cell: ({ getValue, row }) => (
        <button
          onClick={() => onRowSelect?.(row.original)}
          className="font-mono text-accent-primary hover:underline text-left"
        >
          {getValue() as string}
        </button>
      ),
    },

    // Amount
    {
      accessorKey: 'amount',
      header: 'Amount',
      cell: ({ getValue }) => {
        const amount = getValue() as number
        return amount ? `$${amount.toLocaleString()}` : 'N/A'
      },
    },

    // Acreage
    {
      accessorKey: 'acreage',
      header: 'Acreage',
      cell: ({ getValue }) => {
        const acreage = getValue() as number
        return acreage ? `${acreage.toFixed(2)} ac` : 'N/A'
      },
    },

    // Price per Acre
    {
      accessorKey: 'price_per_acre',
      header: 'Price/Acre',
      cell: ({ getValue }) => {
        const price = getValue() as number
        return price ? `$${price.toLocaleString()}` : 'N/A'
      },
    },

    // Investment Grade (based on buy_hold_score)
    {
      id: 'investment_grade',
      header: () => (
        <div className="flex items-center gap-1">
          <span>Grade</span>
          <ScoreTooltip scoreType="investment_grade" iconSize={12} />
        </div>
      ),
      cell: ({ row }) => (
        <InvestmentGradeBadge score={row.original.buy_hold_score} size="sm" />
      ),
      enableSorting: false,
    },

    // Effective Cost (total cost including quiet title)
    {
      accessorKey: 'effective_cost',
      header: () => (
        <div className="flex items-center gap-1">
          <span>Total Cost</span>
          <ScoreTooltip scoreType="effective_cost" iconSize={12} />
        </div>
      ),
      cell: ({ getValue, row }) => {
        const cost = getValue() as number
        const budget = 8000 // Could be from user preferences
        const isOverBudget = cost && cost > budget
        const isMarketReject = row.original.is_market_reject
        const isDeltaRegion = row.original.is_delta_region

        return (
          <div className="flex items-center gap-1">
            <span className={isOverBudget ? 'text-danger' : 'text-text-primary'}>
              {cost ? `$${cost.toLocaleString()}` : 'N/A'}
            </span>
            {isMarketReject && (
              <span title="Market Reject: Pre-2015 delinquency">
                <AlertTriangle className="w-3 h-3 text-danger" />
              </span>
            )}
            {isDeltaRegion && (
              <span title="Delta Region: Economically distressed area">
                <AlertTriangle className="w-3 h-3 text-warning" />
              </span>
            )}
          </div>
        )
      },
    },

    // Buy & Hold Score
    {
      accessorKey: 'buy_hold_score',
      header: () => (
        <div className="flex items-center gap-1">
          <span>B&H Score</span>
          <ScoreTooltip scoreType="buy_hold_score" iconSize={12} />
        </div>
      ),
      cell: ({ getValue }) => {
        const score = getValue() as number
        if (!score) return 'N/A'

        const color = score >= 80 ? 'text-success' :
                     score >= 60 ? 'text-accent-primary' :
                     score >= 40 ? 'text-warning' : 'text-danger'

        return (
          <span className={`font-semibold ${color}`}>
            {score.toFixed(1)}
          </span>
        )
      },
    },

    // Investment Score
    {
      accessorKey: 'investment_score',
      header: () => (
        <div className="flex items-center gap-1">
          <span>Inv Score</span>
          <ScoreTooltip scoreType="investment_score" iconSize={12} />
        </div>
      ),
      cell: ({ getValue }) => {
        const score = getValue() as number
        if (!score) return 'N/A'

        const color = score >= 80 ? 'text-success' :
                     score >= 60 ? 'text-accent-primary' :
                     score >= 40 ? 'text-warning' : 'text-danger'

        return (
          <span className={`font-semibold ${color}`}>
            {score.toFixed(1)}
          </span>
        )
      },
    },

    // Water Score
    {
      accessorKey: 'water_score',
      header: () => (
        <div className="flex items-center gap-1">
          <span>Water</span>
          <ScoreTooltip scoreType="water_score" iconSize={12} />
        </div>
      ),
      cell: ({ getValue }) => {
        const score = getValue() as number
        return score ? (
          <span className="text-accent-secondary">{score.toFixed(1)}</span>
        ) : 'N/A'
      },
    },

    // County
    {
      accessorKey: 'county',
      header: 'County',
      cell: ({ getValue }) => getValue() as string || 'Unknown',
    },

    // State
    {
      accessorKey: 'state',
      header: 'State',
      cell: ({ getValue }) => getValue() as string || 'AL',
    },

    // Description (truncated)
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ getValue }) => {
        const desc = getValue() as string
        return desc ? (
          <span className="text-sm text-text-muted" title={desc}>
            {desc.length > 50 ? `${desc.substring(0, 50)}...` : desc}
          </span>
        ) : 'No description'
      },
    },

    // Owner Name
    {
      accessorKey: 'owner_name',
      header: 'Owner',
      cell: ({ getValue }) => {
        const owner = getValue() as string
        return owner ? (
          <span className="text-sm">{owner}</span>
        ) : 'Unknown'
      },
    },

    // Year Sold
    {
      accessorKey: 'year_sold',
      header: 'Year Sold',
      cell: ({ getValue }) => getValue() as string || 'N/A',
    },

    // Actions - uses memoized ActionsCell component defined outside to avoid recreation
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <ActionsCell
          property={row.original}
          isWatched={watchlistStatus[row.original.id] || false}
          isToggling={togglingWatch.has(row.original.id)}
          onView={onRowSelect}
          onToggleWatch={toggleWatch}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps -- watchlistStatus and togglingWatch handled by cell render; toggleWatch is stable via refs
  ], [onRowSelect, isInCompare, isAtLimit, toggleCompare])

  // Create table instance
  const table = useReactTable({
    data: stableItems,
    columns,
    pageCount: data?.pages || 1,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      pagination,
    },
    enableRowSelection: true,
    onSortingChange: handleSortingChange,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: handlePaginationChange,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    manualSorting: true,
  })

  // Column visibility toggle component
  const ColumnVisibilityToggle = () => (
    <div className="relative group">
      <button
        className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors flex items-center space-x-2"
        aria-label="Toggle column visibility"
      >
        <EyeOff className="w-4 h-4" />
        <span>Columns</span>
      </button>

      <div className="absolute right-0 top-full mt-1 w-56 bg-card border border-neutral-1 rounded-lg shadow-elevated z-50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto">
        <div className="p-3">
          <h4 className="text-sm font-medium text-text-primary mb-2">Toggle Columns</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {table.getAllLeafColumns()
              .filter(column => column.getCanHide())
              .map(column => (
                <label key={column.id} className="flex items-center space-x-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={column.getIsVisible()}
                    onChange={column.getToggleVisibilityHandler()}
                    className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
                  />
                  <span className="text-text-primary">
                    {typeof column.columnDef.header === 'string'
                      ? column.columnDef.header
                      : column.id}
                  </span>
                </label>
              ))}
          </div>
        </div>
      </div>
    </div>
  )

  // Bulk add to watchlist (parallel execution)
  const bulkAddToWatchlist = async () => {
    const selectedRows = table.getFilteredSelectedRowModel().rows
    const propertyIds = selectedRows.map(row => row.original.id)
    // Use ref to get current status (avoids stale closure)
    const toAdd = propertyIds.filter(id => !watchlistStatusRef.current[id])

    if (toAdd.length === 0) {
      showToast.info('All selected properties are already in your watchlist')
      return
    }

    setBulkLoading(true)

    // Parallel execution with Promise.allSettled
    const results = await Promise.allSettled(
      toAdd.map(async (propertyId) => {
        const result = await api.watchlist.toggleWatch(propertyId)
        return { propertyId, is_watched: result.is_watched }
      })
    )

    // Process results
    const newStatus: WatchlistStatus = {}
    let successCount = 0

    for (const result of results) {
      if (result.status === 'fulfilled') {
        newStatus[result.value.propertyId] = result.value.is_watched
        successCount++
      }
    }

    // Batch state update (single re-render)
    setWatchlistStatus(prev => ({ ...prev, ...newStatus }))
    setBulkLoading(false)

    if (successCount > 0) {
      showToast.success(`Added ${successCount} properties to watchlist`)
    }
    if (successCount < toAdd.length) {
      showToast.warning(`${toAdd.length - successCount} properties failed to add`)
    }

    // Clear selection after bulk action
    table.resetRowSelection()
  }

  // Share URL handler
  const handleShareUrl = async () => {
    const success = await copyUrlToClipboard()
    if (success) {
      showToast.success('Link copied to clipboard', {
        description: 'Share this link to show the same filtered view'
      })
    } else {
      showToast.error('Failed to copy link')
    }
  }

  // Bulk actions component
  const BulkActions = () => {
    const selectedRows = table.getFilteredSelectedRowModel().rows

    if (selectedRows.length === 0) return null

    return (
      <div className="flex items-center space-x-2 p-3 bg-accent-primary/10 border border-accent-primary/20 rounded-lg">
        <span className="text-sm text-accent-primary font-medium">
          {selectedRows.length} row(s) selected
        </span>
        <div className="flex space-x-2 ml-auto">
          <button
            onClick={bulkAddToWatchlist}
            disabled={bulkLoading}
            className="px-3 py-1 bg-accent-primary text-white text-sm rounded hover:bg-opacity-90 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            {bulkLoading && <Loader2 className="w-3 h-3 animate-spin" />}
            Add to Watchlist
          </button>
          <button className="px-3 py-1 bg-surface text-text-primary border border-neutral-1 text-sm rounded hover:bg-card transition-colors flex items-center space-x-1">
            <Download className="w-3 h-3" />
            <span>Export</span>
          </button>
        </div>
      </div>
    )
  }

  // Compare actions component - renders as sticky footer bar
  const CompareActions = () => {
    if (compareCount === 0) return null

    return (
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center space-x-3 px-5 py-3 bg-card border border-accent-secondary rounded-full shadow-elevated animate-in slide-in-from-bottom-4 duration-200">
        <GitCompare className="w-5 h-5 text-accent-secondary" />
        <span className="text-sm font-medium text-text-primary">
          {compareCount} of 3 selected
        </span>
        <button
          onClick={() => setShowCompareModal(true)}
          className="px-4 py-1.5 bg-accent-secondary text-white text-sm font-semibold rounded-full hover:bg-opacity-90 transition-colors"
        >
          Compare Now
        </button>
        <button
          onClick={clearCompare}
          className="px-2 py-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
          aria-label="Clear comparison selection"
        >
          Clear
        </button>
      </div>
    )
  }

  // Determine empty state type
  const hasFiltersApplied = activeFilterCount > 0 || searchQuery

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Error State */}
      {error && (
        <ErrorState
          error={error}
          onRetry={refetch}
          compact
        />
      )}

      {/* Table Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm text-text-muted">
            {loading ? 'Loading...' : `${data?.total || 0} properties`}
          </span>
          {data?.total !== undefined && data.total > 0 && (
            <span className="text-xs text-text-muted">
              (Page {pagination.pageIndex + 1} of {data.pages})
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleShareUrl}
            className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors flex items-center space-x-2"
            title="Copy shareable link"
            aria-label="Copy shareable link"
          >
            <Share2 className="w-4 h-4" />
            <span className="hidden sm:inline">Share</span>
          </button>

          <ColumnVisibilityToggle />

          <select
            value={pagination.pageSize}
            onChange={(e) => {
              setPerPage(Number(e.target.value))
              setPage(1)
            }}
            className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
            aria-label="Rows per page"
          >
            <option value={10}>10 per page</option>
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      <BulkActions />

      {/* Compare Actions */}
      <CompareActions />

      {/* Table */}
      <div className={`flex-1 min-h-0 bg-card rounded-lg border border-neutral-1 shadow-card overflow-hidden ${hasBanners ? 'pb-20' : ''}`}>
        <div className="h-full overflow-auto">
          <table className="w-full">
            <thead className="bg-surface border-b border-neutral-1 sticky top-0 z-10">
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th key={header.id} className="px-4 py-3 text-left">
                      {header.isPlaceholder ? null : (
                        <div
                          className={`flex items-center space-x-1 ${
                            header.column.getCanSort() ? 'cursor-pointer select-none' : ''
                          }`}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <span className="text-sm font-medium text-text-primary">
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                          </span>
                          {header.column.getCanSort() && (
                            <span className="text-text-muted">
                              {header.column.getIsSorted() === 'desc' ? (
                                <ChevronDown className="w-4 h-4" />
                              ) : header.column.getIsSorted() === 'asc' ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <div className="w-4 h-4" />
                              )}
                            </span>
                          )}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>

            <tbody>
              {(() => {
                const rows = table.getRowModel().rows
                const hasRows = rows.length > 0
                // Only show skeleton when loading AND no existing rows to display
                const showSkeleton = loading && !hasRows
                const showEmpty = !loading && !hasRows

                if (showSkeleton) {
                  return (
                    <tr>
                      <td colSpan={columns.length}>
                        <TableSkeleton rows={pagination.pageSize} columns={columns.length} showHeader={false} />
                      </td>
                    </tr>
                  )
                }

                if (showEmpty) {
                  return (
                    <tr>
                      <td colSpan={columns.length}>
                        {hasFiltersApplied ? (
                          <FilterEmptyState
                            activeFilterCount={activeFilterCount}
                            onResetFilters={resetFilters}
                          />
                        ) : (
                          <EmptyState
                            type="no-data"
                            title="No properties yet"
                            description="Start by running a scrape job or importing data to populate your property database."
                            actionLabel="Go to Scrape Jobs"
                            onAction={() => window.location.href = '/scrape-jobs'}
                          />
                        )}
                      </td>
                    </tr>
                  )
                }

                // Always render rows if we have them (prevents flash on refetch)
                return rows.map(row => (
                  <tr
                    key={row.id}
                    className="border-b border-neutral-1 hover:bg-surface transition-colors"
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-3 text-text-primary">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              })()}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-neutral-1">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
                className="px-3 py-1 text-sm border border-neutral-1 rounded hover:bg-surface transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Go to first page"
              >
                First
              </button>
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="px-3 py-1 text-sm border border-neutral-1 rounded hover:bg-surface transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Go to previous page"
              >
                Previous
              </button>
            </div>

            <span className="text-sm text-text-muted">
              Page {pagination.pageIndex + 1} of {data.pages}
            </span>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="px-3 py-1 text-sm border border-neutral-1 rounded hover:bg-surface transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Go to next page"
              >
                Next
              </button>
              <button
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
                className="px-3 py-1 text-sm border border-neutral-1 rounded hover:bg-surface transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Go to last page"
              >
                Last
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
