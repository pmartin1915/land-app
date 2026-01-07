import React, { useState, useMemo, useEffect, useCallback } from 'react'
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
  Loader2
} from 'lucide-react'
import { Property, PropertyFilters, SearchParams } from '../types'
import { useProperties } from '../lib/hooks'
import { useUrlState } from '../lib/useUrlState'
import { TableSkeleton } from './ui/LoadingSkeleton'
import { ErrorState } from './ui/ErrorState'
import { EmptyState, FilterEmptyState } from './ui/EmptyState'
import { showToast } from './ui/Toast'

interface PropertiesTableProps {
  onRowSelect?: (property: Property | null) => void
  globalFilters?: PropertyFilters
  searchQuery?: string
}

// Watchlist status cache
interface WatchlistStatus {
  [propertyId: string]: boolean
}

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

  // Table state - sync with URL state
  const [sorting, setLocalSorting] = useState<SortingState>(() =>
    sortBy ? [{ id: sortBy, desc: sortOrder === 'desc' }] : []
  )
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [pagination, setLocalPagination] = useState({
    pageIndex: page - 1,
    pageSize: perPage,
  })

  // Watchlist state
  const [watchlistStatus, setWatchlistStatus] = useState<WatchlistStatus>({})
  const [togglingWatch, setTogglingWatch] = useState<string | null>(null)
  const [bulkLoading, setBulkLoading] = useState(false)

  // Sync URL state with local state
  useEffect(() => {
    if (sorting.length > 0) {
      setSorting(sorting[0].id, sorting[0].desc ? 'desc' : 'asc')
    } else {
      setSorting(undefined, undefined)
    }
  }, [sorting, setSorting])

  useEffect(() => {
    setPage(pagination.pageIndex + 1)
    setPerPage(pagination.pageSize)
  }, [pagination, setPage, setPerPage])

  // Build search params for API
  const searchParams: SearchParams = useMemo(() => ({
    q: searchQuery,
    filters: globalFilters,
    sort_by: sorting[0]?.id,
    sort_order: sorting[0]?.desc ? 'desc' : 'asc',
    page: pagination.pageIndex + 1,
    per_page: pagination.pageSize,
  }), [searchQuery, globalFilters, sorting, pagination])

  // Fetch data
  const { data, isLoading: loading, error, refetch } = useProperties(searchParams)

  // Fetch watchlist status for visible properties
  const fetchWatchlistStatus = useCallback(async (propertyIds: string[]) => {
    if (propertyIds.length === 0) return

    try {
      const response = await fetch(`/api/v1/watchlist/bulk-status?property_ids=${propertyIds.join(',')}`, {
        headers: {
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        }
      })

      if (response.ok) {
        const statusData = await response.json()
        setWatchlistStatus(prev => ({ ...prev, ...statusData }))
      }
    } catch (err) {
      console.error('Failed to fetch watchlist status:', err)
    }
  }, [])

  // Fetch watchlist status when data changes
  useEffect(() => {
    if (data?.items) {
      const propertyIds = data.items.map(p => p.id)
      fetchWatchlistStatus(propertyIds)
    }
  }, [data?.items, fetchWatchlistStatus])

  // Toggle watch status for a property
  const toggleWatch = useCallback(async (propertyId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (togglingWatch) return

    const wasWatched = watchlistStatus[propertyId] || false

    try {
      setTogglingWatch(propertyId)
      // Optimistic update
      setWatchlistStatus(prev => ({
        ...prev,
        [propertyId]: !wasWatched
      }))

      const response = await fetch(`/api/v1/watchlist/property/${propertyId}/watch`, {
        method: 'POST',
        headers: {
          'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
        }
      })

      if (response.ok) {
        const result = await response.json()
        setWatchlistStatus(prev => ({
          ...prev,
          [propertyId]: result.is_watched
        }))
        showToast.success(
          result.is_watched ? 'Added to watchlist' : 'Removed from watchlist'
        )
      } else {
        // Revert on error
        setWatchlistStatus(prev => ({
          ...prev,
          [propertyId]: wasWatched
        }))
        showToast.error('Failed to update watchlist')
      }
    } catch (err) {
      // Revert on error
      setWatchlistStatus(prev => ({
        ...prev,
        [propertyId]: wasWatched
      }))
      showToast.error('Failed to update watchlist')
    } finally {
      setTogglingWatch(null)
    }
  }, [togglingWatch, watchlistStatus])

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

    // Investment Score
    {
      accessorKey: 'investment_score',
      header: 'Investment Score',
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
      header: 'Water Score',
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

    // Actions - note: this column uses external state, but we handle it via cell render
    {
      id: 'actions',
      header: 'Actions',
      cell: function ActionsCell({ row }) {
        const propertyId = row.original.id
        const isWatched = watchlistStatus[propertyId] || false
        const isToggling = togglingWatch === propertyId

        return (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onRowSelect?.(row.original)}
              className="p-1 hover:bg-surface rounded transition-colors"
              title="View Details"
              aria-label="View property details"
            >
              <Eye className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => toggleWatch(propertyId, e)}
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
      },
      enableSorting: false,
      enableHiding: false,
    },
  ], [onRowSelect, watchlistStatus, togglingWatch, toggleWatch])

  // Create table instance
  const table = useReactTable({
    data: data?.items || [],
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
    onSortingChange: setLocalSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: setLocalPagination,
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

  // Bulk add to watchlist
  const bulkAddToWatchlist = async () => {
    const selectedRows = table.getFilteredSelectedRowModel().rows
    const propertyIds = selectedRows.map(row => row.original.id)
    const toAdd = propertyIds.filter(id => !watchlistStatus[id])

    if (toAdd.length === 0) {
      showToast.info('All selected properties are already in your watchlist')
      return
    }

    setBulkLoading(true)
    let successCount = 0

    for (const propertyId of toAdd) {
      try {
        const response = await fetch(`/api/v1/watchlist/property/${propertyId}/watch`, {
          method: 'POST',
          headers: {
            'X-API-Key': localStorage.getItem('aw_api_key') || 'AW_dev_automated_development_key_001'
          }
        })

        if (response.ok) {
          const result = await response.json()
          setWatchlistStatus(prev => ({
            ...prev,
            [propertyId]: result.is_watched
          }))
          successCount++
        }
      } catch (err) {
        console.error('Failed to add to watchlist:', err)
      }
    }

    setBulkLoading(false)

    if (successCount > 0) {
      showToast.success(`Added ${successCount} properties to watchlist`)
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

  // Determine empty state type
  const hasFiltersApplied = activeFilterCount > 0 || searchQuery

  return (
    <div className="space-y-4">
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
            onChange={(e) => setLocalPagination(prev => ({ ...prev, pageSize: Number(e.target.value), pageIndex: 0 }))}
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

      {/* Table */}
      <div className="bg-card rounded-lg border border-neutral-1 shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface border-b border-neutral-1">
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
              {loading ? (
                // Loading skeleton
                <tr>
                  <td colSpan={columns.length}>
                    <TableSkeleton rows={pagination.pageSize} columns={columns.length} showHeader={false} />
                  </td>
                </tr>
              ) : table.getRowModel().rows.length === 0 ? (
                // Empty state
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
              ) : (
                // Data rows
                table.getRowModel().rows.map(row => (
                  <tr
                    key={row.id}
                    className="border-b border-neutral-1 hover:bg-surface transition-colors"
                  >
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
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
