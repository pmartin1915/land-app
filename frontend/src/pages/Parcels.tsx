import { useState, useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Property, PropertyFilters } from '../types'
import { PropertiesTable } from '../components/PropertiesTable'
import { PropertyDetailSlideOver } from '../components/PropertyDetailSlideOver'
import { ScoreTooltip } from '../components/ui/ScoreTooltip'
import { Tooltip } from '../components/ui/Tooltip'
import { Droplets, Sparkles, X, Maximize2, Minimize2, Search } from 'lucide-react'

const STATE_OPTIONS = [
  { value: '', label: 'All States' },
  { value: 'AL', label: 'Alabama' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'TX', label: 'Texas' },
  { value: 'FL', label: 'Florida' },
]

export function Parcels() {
  const [, setSearchParams] = useSearchParams()
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [slideOverOpen, setSlideOverOpen] = useState(false)
  // Staged filters pattern: draftFilters for UI edits, appliedFilters sent to API
  const [draftFilters, setDraftFilters] = useState<PropertyFilters>({})
  const [appliedFilters, setAppliedFilters] = useState<PropertyFilters>({})
  const [beginnerFriendly, setBeginnerFriendly] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  // Check if draft filters differ from applied filters
  const hasUnappliedChanges = useMemo(() => {
    return JSON.stringify(draftFilters) !== JSON.stringify(appliedFilters)
  }, [draftFilters, appliedFilters])

  // Count active filters (based on draft for UI display)
  const activeFilterCount = [
    draftFilters.state,
    draftFilters.minInvestmentScore,
    draftFilters.maxEffectiveCost,
    draftFilters.acreageRange,
    draftFilters.waterOnly,
    beginnerFriendly,
  ].filter(Boolean).length

  // Apply filters - copy draft to applied
  const handleApplyFilters = useCallback(() => {
    setAppliedFilters(draftFilters)
  }, [draftFilters])

  // Handle state filter change
  const handleStateChange = (state: string) => {
    setDraftFilters(prev => ({
      ...prev,
      state: state || undefined
    }))
  }

  // Handle investment score filter change
  const handleInvestmentScoreChange = (score: string) => {
    const parsed = parseInt(score, 10)
    setDraftFilters(prev => ({
      ...prev,
      minInvestmentScore: isNaN(parsed) ? undefined : parsed
    }))
  }

  // Handle max budget filter change
  const handleMaxBudgetChange = (budget: string) => {
    const parsed = parseInt(budget, 10)
    setDraftFilters(prev => ({
      ...prev,
      maxEffectiveCost: isNaN(parsed) ? undefined : parsed
    }))
  }

  // Handle min acreage filter change
  const handleMinAcreageChange = (acreage: string) => {
    const parsed = parseFloat(acreage)
    setDraftFilters(prev => {
      const currentMax = prev.acreageRange?.[1]
      if (isNaN(parsed)) {
        // Remove min, keep max if exists
        return {
          ...prev,
          acreageRange: currentMax ? [0, currentMax] : undefined
        }
      }
      return {
        ...prev,
        acreageRange: [parsed, currentMax || 1000]
      }
    })
  }

  // Handle max acreage filter change
  const handleMaxAcreageChange = (acreage: string) => {
    const parsed = parseFloat(acreage)
    setDraftFilters(prev => {
      const currentMin = prev.acreageRange?.[0] || 0
      if (isNaN(parsed)) {
        // Remove max, keep min if exists
        return {
          ...prev,
          acreageRange: currentMin > 0 ? [currentMin, 1000] : undefined
        }
      }
      return {
        ...prev,
        acreageRange: [currentMin, parsed]
      }
    })
  }

  // Handle water only filter change
  const handleWaterOnlyChange = (checked: boolean) => {
    setDraftFilters(prev => ({
      ...prev,
      waterOnly: checked || undefined
    }))
  }

  // Handle beginner friendly toggle - auto-applies as it's a preset
  const handleBeginnerFriendlyToggle = useCallback((enabled: boolean) => {
    setBeginnerFriendly(enabled)
    const newFilters = enabled
      ? { state: 'AR' as const, minBuyHoldScore: 25 }
      : {}
    setDraftFilters(newFilters)
    setAppliedFilters(newFilters) // Auto-apply presets immediately
  }, [])

  // Clear all filters
  const handleClearFilters = () => {
    setDraftFilters({})
    setAppliedFilters({})
    setBeginnerFriendly(false)
  }

  // Handle property selection from table
  const handlePropertySelect = useCallback((property: Property | null) => {
    setSelectedProperty(property)
    setSlideOverOpen(!!property)

    // Update URL with selected property ID while preserving existing params
    setSearchParams(prev => {
      const newParams = new URLSearchParams(prev)
      if (property) {
        newParams.set('selected', property.id)
      } else {
        newParams.delete('selected')
      }
      return newParams
    }, { replace: true })
  }, [setSearchParams])

  // Close slide over
  const handleCloseSlideOver = useCallback(() => {
    setSlideOverOpen(false)
    setSelectedProperty(null)
    setSearchParams(prev => {
      const newParams = new URLSearchParams(prev)
      newParams.delete('selected')
      return newParams
    }, { replace: true })
  }, [setSearchParams])

  // Handle Escape key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isExpanded])

  return (
    <div className={`h-full flex flex-col transition-all duration-200 ${isExpanded ? 'fixed inset-0 z-50 bg-bg p-4' : 'p-6'}`}>
      {/* Header with expand/minimize button */}
      <div className={`flex items-center justify-between ${isExpanded ? 'mb-3' : 'mb-6'}`}>
        <div>
          <h1 className={`font-bold text-text-primary ${isExpanded ? 'text-xl' : 'text-2xl'} mb-1`}>Parcels</h1>
          {!isExpanded && <p className="text-text-muted">Primary work area - List + Detail</p>}
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors"
          aria-label={isExpanded ? 'Minimize view' : 'Expand view'}
          title={isExpanded ? 'Exit fullscreen (Esc)' : 'Fullscreen view'}
        >
          {isExpanded ? (
            <>
              <Minimize2 className="w-4 h-4" />
              <span className="text-sm">Minimize</span>
            </>
          ) : (
            <>
              <Maximize2 className="w-4 h-4" />
              <span className="text-sm">Expand</span>
            </>
          )}
        </button>
      </div>

      {/* Filter Bar - horizontally scrollable on smaller screens */}
      <div className="mb-4 space-y-3 overflow-x-auto pb-2">
        {/* Primary Filters Row */}
        <div className="flex items-center gap-4 min-w-max">
          {/* Beginner Friendly Toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBeginnerFriendlyToggle(!beginnerFriendly)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${beginnerFriendly
                  ? 'bg-success text-white'
                  : 'bg-surface text-text-primary border border-neutral-1 hover:bg-card'
                }
              `}
              aria-pressed={beginnerFriendly}
              aria-label="Toggle beginner-friendly filter (Arkansas only, score > 25)"
            >
              <Sparkles className="w-4 h-4" />
              <span>Beginner Friendly</span>
            </button>
            <Tooltip
              content={
                <div className="text-xs space-y-1">
                  <p className="font-medium">Beginner Friendly Filter</p>
                  <p className="text-text-muted">Shows only Arkansas properties with Buy & Hold score above 25.</p>
                  <p className="text-text-muted">Arkansas is ideal for beginners due to short 30-day redemption and low quiet title costs.</p>
                </div>
              }
              showHelpIcon
              iconSize={14}
            />
          </div>

          {/* State Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="state-filter" className="text-sm font-medium text-text-primary">State:</label>
            <select
              id="state-filter"
              value={draftFilters.state || ''}
              onChange={(e) => handleStateChange(e.target.value)}
              aria-label="Filter properties by state"
              disabled={beginnerFriendly}
              className={`
                px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm
                focus:outline-none focus:ring-2 focus:ring-accent-primary
                ${beginnerFriendly ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {STATE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Max Budget Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="budget-filter" className="text-sm font-medium text-text-primary">Max Budget:</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">$</span>
              <input
                id="budget-filter"
                type="number"
                min="0"
                step="1000"
                placeholder="8000"
                value={draftFilters.maxEffectiveCost ?? ''}
                onChange={(e) => handleMaxBudgetChange(e.target.value)}
                aria-label="Filter properties by maximum effective cost"
                className="w-28 pl-7 pr-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
              />
            </div>
            <ScoreTooltip scoreType="effective_cost" iconSize={14} />
          </div>

          {/* Min Score Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="score-filter" className="text-sm font-medium text-text-primary">Min Score:</label>
            <input
              id="score-filter"
              type="number"
              min="0"
              max="100"
              placeholder="0-100"
              value={draftFilters.minInvestmentScore ?? ''}
              onChange={(e) => handleInvestmentScoreChange(e.target.value)}
              aria-label="Filter properties by minimum investment score"
              className="w-24 px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
            <ScoreTooltip scoreType="investment_score" iconSize={14} />
          </div>
        </div>

        {/* Secondary Filters Row */}
        <div className="flex items-center gap-4 min-w-max">
          {/* Acreage Range */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-text-primary">Acreage:</label>
            <input
              type="number"
              min="0"
              step="0.5"
              placeholder="Min"
              value={draftFilters.acreageRange?.[0] ?? ''}
              onChange={(e) => handleMinAcreageChange(e.target.value)}
              aria-label="Minimum acreage"
              className="w-20 px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
            <span className="text-text-muted">-</span>
            <input
              type="number"
              min="0"
              step="0.5"
              placeholder="Max"
              value={draftFilters.acreageRange?.[1] ?? ''}
              onChange={(e) => handleMaxAcreageChange(e.target.value)}
              aria-label="Maximum acreage"
              className="w-20 px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
            />
            <span className="text-sm text-text-muted">ac</span>
          </div>

          {/* Water Access Checkbox */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={draftFilters.waterOnly || false}
              onChange={(e) => handleWaterOnlyChange(e.target.checked)}
              aria-label="Filter properties with water access"
              className="w-4 h-4 rounded border-neutral-1 text-accent-primary focus:ring-accent-primary"
            />
            <Droplets className="w-4 h-4 text-accent-secondary" />
            <span className="text-sm font-medium text-text-primary">Water Access</span>
            <ScoreTooltip scoreType="water_score" iconSize={14} />
          </label>

          {/* Apply Filters Button - shows when changes are pending */}
          {hasUnappliedChanges && (
            <button
              onClick={handleApplyFilters}
              className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white text-sm font-medium rounded-lg hover:bg-accent-primary/90 transition-colors"
              aria-label="Apply filter changes"
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </button>
          )}

          {/* Clear Filters Button */}
          {activeFilterCount > 0 && (
            <button
              onClick={handleClearFilters}
              className="flex items-center gap-1 px-3 py-2 text-sm text-danger hover:bg-danger/10 rounded-lg transition-colors"
              aria-label="Clear all filters"
            >
              <X className="w-4 h-4" />
              <span>Clear ({activeFilterCount})</span>
            </button>
          )}
        </div>
      </div>

      {/* Properties Table */}
      <div className="flex-1 min-h-0">
        <PropertiesTable onRowSelect={handlePropertySelect} globalFilters={appliedFilters} />
      </div>

      {/* Property Detail Slide Over */}
      <PropertyDetailSlideOver
        property={selectedProperty}
        isOpen={slideOverOpen}
        onClose={handleCloseSlideOver}
      />
    </div>
  )
}
