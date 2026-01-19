import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ThemeToggle } from '../lib/theme-provider'
import { usePropertySearch, useCounties } from '../lib/hooks'
import { PropertyFilters } from '../types'
import { Search, Filter, Download, Upload, Settings, Calendar, ChevronDown, X } from 'lucide-react'
import { SearchEmptyState } from './ui/EmptyState'
import { showToast } from './ui/Toast'
import { CSVImportModal } from './CSVImportModal'

interface TopBarProps {
  title: string
  onFiltersChange?: (filters: PropertyFilters) => void
  onSearchChange?: (query: string, results: unknown[]) => void
}

interface FilterPopoverProps {
  isOpen: boolean
  onClose: () => void
  filters: PropertyFilters
  onFiltersChange: (filters: PropertyFilters) => void
}

function FilterPopover({ isOpen, onClose, filters, onFiltersChange }: FilterPopoverProps) {
  const { data: counties = [] } = useCounties()
  const [localFilters, setLocalFilters] = useState<PropertyFilters>(filters)

  const handleApplyFilters = () => {
    onFiltersChange(localFilters)
    onClose()
    showToast.success('Filters applied')
  }

  const handleResetFilters = () => {
    const resetFilters: PropertyFilters = {}
    setLocalFilters(resetFilters)
    onFiltersChange(resetFilters)
    onClose()
    showToast.info('Filters reset')
  }

  // Handle escape key
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-transparent"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Popover */}
      <div className="absolute top-full right-0 mt-2 z-50 w-96 bg-card border border-neutral-1 rounded-lg shadow-elevated p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary">Advanced Filters</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-surface rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Price Range */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            Price Range
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              placeholder="Min"
              value={localFilters.priceRange?.[0] || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                priceRange: [parseInt(e.target.value) || 0, localFilters.priceRange?.[1] || 100000]
              })}
              className="flex-1 px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
            <input
              type="number"
              placeholder="Max"
              value={localFilters.priceRange?.[1] || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                priceRange: [localFilters.priceRange?.[0] || 0, parseInt(e.target.value) || 100000]
              })}
              className="flex-1 px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
        </div>

        {/* Acreage Range */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            Acreage Range
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              step="0.1"
              placeholder="Min"
              value={localFilters.acreageRange?.[0] || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                acreageRange: [parseFloat(e.target.value) || 0, localFilters.acreageRange?.[1] || 100]
              })}
              className="flex-1 px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
            <input
              type="number"
              step="0.1"
              placeholder="Max"
              value={localFilters.acreageRange?.[1] || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                acreageRange: [localFilters.acreageRange?.[0] || 0, parseFloat(e.target.value) || 100]
              })}
              className="flex-1 px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
        </div>

        {/* State Selection */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            State
          </label>
          <select
            value={localFilters.state || ''}
            onChange={(e) => setLocalFilters({
              ...localFilters,
              state: e.target.value || undefined,
              county: undefined // Reset county when state changes
            })}
            className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
          >
            <option value="">All States</option>
            <option value="AL">Alabama (Tax Lien)</option>
            <option value="AR">Arkansas (Tax Deed)</option>
          </select>
        </div>

        {/* County Selection */}
        <div>
          <label className="block text-sm font-medium text-text-primary mb-2">
            County
          </label>
          <select
            value={localFilters.county || ''}
            onChange={(e) => setLocalFilters({
              ...localFilters,
              county: e.target.value || undefined
            })}
            className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
          >
            <option value="">All Counties</option>
            {counties.map((county) => (
              <option key={county.code} value={county.name}>
                {county.name}
              </option>
            ))}
          </select>
        </div>

        {/* Water Only Toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="water-only"
            checked={localFilters.waterOnly || false}
            onChange={(e) => setLocalFilters({
              ...localFilters,
              waterOnly: e.target.checked || undefined
            })}
            className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
          />
          <label htmlFor="water-only" className="ml-2 text-sm text-text-primary">
            Water access only
          </label>
        </div>

        {/* Hide Stale Delinquencies Toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="hide-stale"
            checked={localFilters.minYearSold === 2015}
            onChange={(e) => setLocalFilters({
              ...localFilters,
              minYearSold: e.target.checked ? 2015 : undefined
            })}
            className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
          />
          <label htmlFor="hide-stale" className="ml-2 text-sm text-text-primary">
            Hide stale delinquencies (pre-2015)
          </label>
        </div>

        {/* Exclude Delta Region Toggle */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="exclude-delta"
            checked={localFilters.excludeDeltaRegion || false}
            onChange={(e) => setLocalFilters({
              ...localFilters,
              excludeDeltaRegion: e.target.checked || undefined
            })}
            className="w-4 h-4 text-accent-primary border-neutral-1 rounded focus:ring-accent-primary"
          />
          <label htmlFor="exclude-delta" className="ml-2 text-sm text-text-primary">
            Exclude Delta region (AR high-risk counties)
          </label>
        </div>

        {/* Score Filters */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-primary">Minimum Scores</h4>

          <div>
            <label className="block text-xs text-text-muted mb-1">Investment Score</label>
            <input
              type="number"
              min="0"
              max="100"
              value={localFilters.minInvestmentScore || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                minInvestmentScore: parseInt(e.target.value) || undefined
              })}
              className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1">County Market Score</label>
            <input
              type="number"
              min="0"
              max="100"
              value={localFilters.minCountyMarketScore || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                minCountyMarketScore: parseInt(e.target.value) || undefined
              })}
              className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1">Geographic Score</label>
            <input
              type="number"
              min="0"
              max="100"
              value={localFilters.minGeographicScore || ''}
              onChange={(e) => setLocalFilters({
                ...localFilters,
                minGeographicScore: parseInt(e.target.value) || undefined
              })}
              className="w-full px-3 py-2 bg-surface border border-neutral-1 rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
          </div>
        </div>
      </div>

      <div className="flex space-x-3 mt-6 pt-4 border-t border-neutral-1">
        <button
          onClick={handleResetFilters}
          className="flex-1 px-4 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors"
        >
          Reset
        </button>
        <button
          onClick={handleApplyFilters}
          className="flex-1 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-colors"
        >
          Apply Filters
        </button>
      </div>
    </div>
    </>
  )
}

export function TopBar({ title, onFiltersChange, onSearchChange }: TopBarProps) {
  const navigate = useNavigate()

  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [filters, setFilters] = useState<PropertyFilters>({})
  const [selectedPeriod, setSelectedPeriod] = useState('all-time')

  const searchRef = useRef<HTMLDivElement>(null)
  const filtersRef = useRef<HTMLDivElement>(null)
  const actionsRef = useRef<HTMLDivElement>(null)

  // Use the search hook with debouncing
  const { data: searchResults, isSearching } = usePropertySearch(searchQuery, filters)

  // Handle search result selection
  const handleSelectProperty = (propertyId: string) => {
    navigate(`/parcels?selected=${propertyId}`)
    setSearchQuery('')
  }

  // Handle filter changes
  const handleFiltersChange = (newFilters: PropertyFilters) => {
    setFilters(newFilters)
    onFiltersChange?.(newFilters)
  }

  // Handle search input changes
  const handleSearchChange = (query: string) => {
    setSearchQuery(query)
    onSearchChange?.(query, searchResults)
  }

  // Handle period selector changes
  const handlePeriodChange = (period: string) => {
    setSelectedPeriod(period)
    let createdAfter: string | undefined

    const now = new Date()
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
      case 'all-time':
      default:
        createdAfter = undefined
        break
    }

    const newFilters = { ...filters, createdAfter }
    setFilters(newFilters)
    onFiltersChange?.(newFilters)
  }

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setSearchQuery('')
      }
      if (filtersRef.current && !filtersRef.current.contains(event.target as Node)) {
        setShowFilters(false)
      }
      if (actionsRef.current && !actionsRef.current.contains(event.target as Node)) {
        setShowQuickActions(false)
      }
    }

    if (showFilters || showQuickActions) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showFilters, showQuickActions])

  // Calculate active filter count
  const activeFilterCount = Object.values(filters).filter(value =>
    value !== undefined && value !== null &&
    (Array.isArray(value) ? value.some(v => v !== undefined) : true)
  ).length

  return (
    <div className="h-16 bg-surface border-b border-neutral-1 px-6 flex items-center flex-shrink-0">
      {/* Page Title */}
      <h1 className="text-xl font-semibold text-text-primary mr-8">
        {title}
      </h1>

      {/* Global Search */}
      <div className="flex-1 max-w-md relative" ref={searchRef}>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-muted w-4 h-4" />
          <input
            type="text"
            placeholder="Search properties, owners, parcels..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-bg border border-neutral-1 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent"
          />
          {isSearching && (
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-accent-primary border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>

        {/* Search Results Dropdown */}
        {searchQuery && searchQuery.length > 2 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-neutral-1 rounded-lg shadow-elevated max-h-96 overflow-y-auto z-50">
            {searchResults.length > 0 ? (
              searchResults.slice(0, 10).map((property) => (
                <button
                  key={property.id}
                  onClick={() => handleSelectProperty(property.id)}
                  className="w-full px-4 py-3 text-left hover:bg-surface transition-colors border-b border-neutral-1 last:border-b-0"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-text-primary">
                        {property.parcel_id}
                      </p>
                      <p className="text-sm text-text-muted">
                        {property.description?.substring(0, 60)}...
                      </p>
                      <p className="text-xs text-text-muted">
                        {property.county} • ${property.amount?.toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-accent-primary">
                        Score: {property.investment_score || 'N/A'}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            ) : !isSearching ? (
              <SearchEmptyState
                query={searchQuery}
                onClear={() => setSearchQuery('')}
              />
            ) : null}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="ml-6 flex items-center space-x-2">
        {/* Advanced Filters */}
        <div className="relative" ref={filtersRef}>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`
              px-3 py-2 rounded-lg border transition-colors flex items-center space-x-2
              ${activeFilterCount > 0
                ? 'bg-accent-primary text-white border-accent-primary'
                : 'bg-surface text-text-primary border-neutral-1 hover:bg-card'
              }
            `}
          >
            <Filter className="w-4 h-4" />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="bg-white text-accent-primary text-xs font-medium px-1.5 py-0.5 rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
          <FilterPopover
            isOpen={showFilters}
            onClose={() => setShowFilters(false)}
            filters={filters}
            onFiltersChange={handleFiltersChange}
          />
        </div>

        {/* Quick Actions Dropdown */}
        <div className="relative" ref={actionsRef}>
          <button
            onClick={() => setShowQuickActions(!showQuickActions)}
            className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors flex items-center space-x-2"
          >
            <span>Actions</span>
            <ChevronDown className="w-4 h-4" />
          </button>

          {showQuickActions && (
            <div className="absolute top-full right-0 mt-1 w-48 bg-card border border-neutral-1 rounded-lg shadow-elevated z-50">
              <button
                onClick={() => {
                  navigate('/reports')
                  setShowQuickActions(false)
                }}
                className="w-full px-4 py-2 text-left hover:bg-surface transition-colors flex items-center space-x-2 text-text-primary"
              >
                <Download className="w-4 h-4" />
                <span>Export Data</span>
              </button>
              <button
                onClick={() => {
                  setShowImportModal(true)
                  setShowQuickActions(false)
                }}
                className="w-full px-4 py-2 text-left hover:bg-surface transition-colors flex items-center space-x-2 text-text-primary"
              >
                <Upload className="w-4 h-4" />
                <span>Import CSV</span>
              </button>
              <button
                onClick={() => {
                  navigate('/scrape-jobs')
                  setShowQuickActions(false)
                }}
                className="w-full px-4 py-2 text-left hover:bg-surface transition-colors flex items-center space-x-2 text-text-primary"
              >
                <Calendar className="w-4 h-4" />
                <span>New Scrape</span>
              </button>
              <button
                onClick={() => {
                  navigate('/settings')
                  setShowQuickActions(false)
                }}
                className="w-full px-4 py-2 text-left hover:bg-surface transition-colors flex items-center space-x-2 text-text-primary border-t border-neutral-1"
              >
                <Settings className="w-4 h-4" />
                <span>Settings</span>
              </button>
            </div>
          )}
        </div>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Period Selector */}
        <select
          className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors focus:outline-none focus:ring-2 focus:ring-accent-primary"
          value={selectedPeriod}
          onChange={(e) => handlePeriodChange(e.target.value)}
        >
          <option value="last-24-hours">Last 24 Hours</option>
          <option value="last-7-days">Last 7 Days</option>
          <option value="last-30-days">Last 30 Days</option>
          <option value="last-quarter">Last Quarter</option>
          <option value="last-year">Last Year</option>
          <option value="all-time">All Time</option>
        </select>
      </div>

      {/* CSV Import Modal */}
      <CSVImportModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImportComplete={(result) => {
          if (result.imported > 0) {
            showToast.success(`Successfully imported ${result.imported} properties`)
          }
        }}
      />
    </div>
  )
}