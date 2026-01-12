import React, { useState, useCallback, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  Star,
  X,
  Eye,
  MapPin,
  DollarSign,
  Ruler,
  Award,
  Droplets,
  AlertTriangle,
  CheckCircle,
  Keyboard,
  ArrowUp,
  ArrowDown,
} from 'lucide-react'
import { useTriageQueue, useProperty } from '../lib/hooks'
import { api } from '../lib/api'
import { AISuggestion, Property } from '../types'

// Investment tier labels
const getTierLabel = (tier: string): { label: string; color: string; bg: string } => {
  if (tier.includes('Elite')) {
    return { label: 'ELITE', color: 'text-emerald-400', bg: 'bg-emerald-500/20 border-emerald-500/50' }
  }
  if (tier.includes('Waterfront')) {
    return { label: 'WATERFRONT', color: 'text-blue-400', bg: 'bg-blue-500/20 border-blue-500/50' }
  }
  if (tier.includes('Deep Value')) {
    return { label: 'DEEP VALUE', color: 'text-amber-400', bg: 'bg-amber-500/20 border-amber-500/50' }
  }
  return { label: tier, color: 'text-gray-400', bg: 'bg-gray-500/20 border-gray-500/50' }
}

// Format price
const formatPrice = (amount: number): string => {
  if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(1)}k`
  }
  return `$${amount.toLocaleString()}`
}

interface TriageCardProps {
  suggestion: AISuggestion
  isSelected: boolean
  onSelect: () => void
  index: number
}

function TriageCard({ suggestion, isSelected, onSelect, index }: TriageCardProps) {
  const tier = getTierLabel(suggestion.proposed_value || '')

  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-lg border cursor-pointer transition-all ${
        isSelected
          ? 'bg-accent-primary/10 border-accent-primary shadow-lg'
          : 'bg-card border-neutral-1 hover:border-neutral-2 hover:bg-surface'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`px-2 py-0.5 rounded text-xs font-bold border ${tier.bg} ${tier.color}`}>
          {tier.label}
        </div>
        <span className="text-xs text-text-muted">#{index + 1}</span>
      </div>

      <div className="mb-2">
        <div className="text-sm font-medium text-text-primary truncate">
          {suggestion.reason?.split('.')[0] || 'Investment Opportunity'}
        </div>
        <div className="text-xs text-text-muted mt-1">
          Confidence: {suggestion.confidence?.toFixed(0)}%
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>Parcel ID: {suggestion.parcel_id?.slice(0, 8)}...</span>
        {isSelected && (
          <span className="text-accent-primary font-medium">Selected</span>
        )}
      </div>
    </div>
  )
}

interface PropertyDetailPanelProps {
  suggestion: AISuggestion | null
  property: Property | null
  isLoading: boolean
  onKeep: () => void
  onReject: () => void
  onViewOnMap: () => void
  actionLoading: boolean
}

function PropertyDetailPanel({
  suggestion,
  property,
  isLoading,
  onKeep,
  onReject,
  onViewOnMap,
  actionLoading,
}: PropertyDetailPanelProps) {
  if (!suggestion) {
    return (
      <div className="h-full flex items-center justify-center bg-surface rounded-lg border border-neutral-1">
        <div className="text-center p-8">
          <Eye className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-text-primary mb-2">Select a Property</h3>
          <p className="text-text-muted">
            Choose a property from the queue to view details and take action.
          </p>
        </div>
      </div>
    )
  }

  const tier = getTierLabel(suggestion.proposed_value || '')

  return (
    <div className="h-full flex flex-col bg-card rounded-lg border border-neutral-1 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-neutral-1 bg-surface">
        <div className="flex items-center justify-between mb-2">
          <div className={`px-3 py-1 rounded text-sm font-bold border ${tier.bg} ${tier.color}`}>
            {tier.label}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onViewOnMap}
              className="p-2 rounded-lg bg-card hover:bg-surface border border-neutral-1 transition-colors"
              title="View on Map"
            >
              <MapPin className="w-4 h-4 text-text-muted" />
            </button>
          </div>
        </div>
        <h2 className="text-lg font-semibold text-text-primary">
          Investment Opportunity
        </h2>
        <p className="text-sm text-text-muted font-mono">
          {suggestion.parcel_id}
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="space-y-4">
            {Array(4).fill(0).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-surface rounded w-1/3 mb-2"></div>
                <div className="h-8 bg-surface rounded"></div>
              </div>
            ))}
          </div>
        ) : property ? (
          <>
            {/* AI Reason */}
            <div className="p-4 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-accent-primary flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-text-primary mb-1">AI Analysis</h4>
                  <p className="text-sm text-text-muted">{suggestion.reason}</p>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-surface rounded-lg border border-neutral-1">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign className="w-4 h-4 text-success" />
                  <span className="text-xs text-text-muted">Price</span>
                </div>
                <span className="text-lg font-bold text-text-primary">
                  {formatPrice(property.amount)}
                </span>
              </div>

              <div className="p-3 bg-surface rounded-lg border border-neutral-1">
                <div className="flex items-center gap-2 mb-1">
                  <Ruler className="w-4 h-4 text-accent-primary" />
                  <span className="text-xs text-text-muted">Acreage</span>
                </div>
                <span className="text-lg font-bold text-text-primary">
                  {property.acreage?.toFixed(2) || 'N/A'} ac
                </span>
              </div>

              <div className="p-3 bg-surface rounded-lg border border-neutral-1">
                <div className="flex items-center gap-2 mb-1">
                  <Award className="w-4 h-4 text-warning" />
                  <span className="text-xs text-text-muted">Score</span>
                </div>
                <span className="text-lg font-bold text-text-primary">
                  {property.investment_score?.toFixed(1) || 'N/A'}
                </span>
              </div>

              <div className="p-3 bg-surface rounded-lg border border-neutral-1">
                <div className="flex items-center gap-2 mb-1">
                  <Droplets className="w-4 h-4 text-blue-400" />
                  <span className="text-xs text-text-muted">Water</span>
                </div>
                <span className="text-lg font-bold text-text-primary">
                  {property.water_score > 0 ? `+${property.water_score}` : 'None'}
                </span>
              </div>
            </div>

            {/* Property Details */}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-muted">County</label>
                <p className="text-text-primary font-medium">{property.county || 'Unknown'}</p>
              </div>

              {property.price_per_acre && (
                <div>
                  <label className="text-xs text-text-muted">Price per Acre</label>
                  <p className="text-text-primary font-medium">
                    ${property.price_per_acre.toLocaleString()}
                  </p>
                </div>
              )}

              {property.assessed_value && (
                <div>
                  <label className="text-xs text-text-muted">Assessed Value</label>
                  <p className="text-text-primary font-medium">
                    ${property.assessed_value.toLocaleString()}
                    {property.assessed_value_ratio && (
                      <span className="text-success ml-2">
                        ({(property.assessed_value_ratio * 100).toFixed(0)}% of assessed)
                      </span>
                    )}
                  </p>
                </div>
              )}

              {property.description && (
                <div>
                  <label className="text-xs text-text-muted">Description</label>
                  <p className="text-sm text-text-primary mt-1 p-3 bg-surface rounded border border-neutral-1">
                    {property.description}
                  </p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-8">
            <p className="text-text-muted">Property details not available.</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-t border-neutral-1 bg-surface">
        <div className="flex gap-3">
          <button
            onClick={onReject}
            disabled={actionLoading}
            className="flex-1 px-4 py-3 bg-danger/10 text-danger border border-danger/30 rounded-lg hover:bg-danger/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <X className="w-5 h-5" />
            <span className="font-medium">Reject</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-xs bg-danger/20 rounded">D</kbd>
          </button>

          <button
            onClick={onKeep}
            disabled={actionLoading}
            className="flex-1 px-4 py-3 bg-success/10 text-success border border-success/30 rounded-lg hover:bg-success/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Star className="w-5 h-5" />
            <span className="font-medium">Keep</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-xs bg-success/20 rounded">K</kbd>
          </button>
        </div>
        <p className="text-center text-xs text-text-muted mt-2">
          Use keyboard shortcuts for faster review
        </p>
      </div>
    </div>
  )
}

export function Triage() {
  const navigate = useNavigate()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false)

  // Fetch triage queue
  const { data: triageQueue, isLoading: loading, error, refetch } = useTriageQueue()
  const [actionLoading, setActionLoading] = useState(false)

  // Get currently selected suggestion
  const selectedSuggestion = useMemo(() => {
    if (!triageQueue || triageQueue.length === 0) return null
    return triageQueue[selectedIndex] || null
  }, [triageQueue, selectedIndex])

  // Fetch full property details for selected suggestion
  const { data: selectedProperty, isLoading: propertyLoading } = useProperty(
    selectedSuggestion?.parcel_id || ''
  )

  // Handle keep action - mark as "reviewing" (ready for deeper research)
  const handleKeep = useCallback(async () => {
    if (!selectedSuggestion) {
      console.warn('handleKeep: No suggestion selected')
      return
    }
    if (!selectedProperty) {
      console.warn('handleKeep: Property not loaded yet for suggestion:', selectedSuggestion.parcel_id)
      return
    }
    setActionLoading(true)
    try {
      console.log('handleKeep: Keeping property', selectedProperty.id)
      // Update property status to "reviewing"
      await api.properties.updatePropertyStatus(
        selectedProperty.id,
        'reviewing',
        `Kept from triage: ${selectedSuggestion.reason || 'High priority investment'}`
      )
      // Move to next item
      if (triageQueue && triageQueue.length > 1) {
        const nextIndex = selectedIndex < triageQueue.length - 1 ? selectedIndex : selectedIndex - 1
        setSelectedIndex(Math.max(0, nextIndex))
      }
      refetch()
    } catch (err) {
      console.error('Failed to keep suggestion:', err)
    } finally {
      setActionLoading(false)
    }
  }, [selectedSuggestion, selectedProperty, selectedIndex, triageQueue, refetch])

  // Handle reject action - mark as "rejected"
  const handleReject = useCallback(async () => {
    if (!selectedSuggestion) {
      console.warn('handleReject: No suggestion selected')
      return
    }
    if (!selectedProperty) {
      console.warn('handleReject: Property not loaded yet for suggestion:', selectedSuggestion.parcel_id)
      return
    }
    setActionLoading(true)
    try {
      console.log('handleReject: Rejecting property', selectedProperty.id)
      // Update property status to "rejected"
      await api.properties.updatePropertyStatus(
        selectedProperty.id,
        'rejected',
        'Rejected via triage review'
      )
      // Move to next item
      if (triageQueue && triageQueue.length > 1) {
        const nextIndex = selectedIndex < triageQueue.length - 1 ? selectedIndex : selectedIndex - 1
        setSelectedIndex(Math.max(0, nextIndex))
      }
      refetch()
    } catch (err) {
      console.error('Failed to reject suggestion:', err)
    } finally {
      setActionLoading(false)
    }
  }, [selectedSuggestion, selectedProperty, selectedIndex, triageQueue, refetch])

  // Handle navigation
  const handleNext = useCallback(() => {
    if (triageQueue && selectedIndex < triageQueue.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    }
  }, [selectedIndex, triageQueue])

  const handlePrevious = useCallback(() => {
    if (selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1)
    }
  }, [selectedIndex])

  // Handle view on map
  const handleViewOnMap = useCallback(() => {
    // Navigate to map page with selected property
    navigate(`/map?property=${selectedSuggestion?.parcel_id}`)
  }, [navigate, selectedSuggestion])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key.toLowerCase()) {
        case 'k':
          handleKeep()
          break
        case 'd':
          handleReject()
          break
        case 'arrowdown':
        case 'j':
          e.preventDefault()
          handleNext()
          break
        case 'arrowup':
        case 'n':
          e.preventDefault()
          handlePrevious()
          break
        case '?':
          setShowKeyboardHelp(true)
          break
        case 'escape':
          setShowKeyboardHelp(false)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeep, handleReject, handleNext, handlePrevious])

  // Reset selection when queue changes
  useEffect(() => {
    if (triageQueue && triageQueue.length > 0) {
      setSelectedIndex(prev => Math.min(prev, triageQueue.length - 1))
    }
  }, [triageQueue])

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-neutral-1 bg-card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-primary">Triage Queue</h1>
            <p className="text-sm text-text-muted">
              Review AI-prioritized investment opportunities
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Queue Stats */}
            <div className="text-sm text-text-muted">
              {loading ? 'Loading...' : `${triageQueue?.length || 0} items in queue`}
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-1 bg-surface rounded-lg border border-neutral-1 p-1">
              <button
                onClick={handlePrevious}
                disabled={selectedIndex === 0 || loading}
                className="p-1.5 rounded hover:bg-card disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Previous (Arrow Up or N)"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 text-sm text-text-muted">
                {triageQueue?.length ? `${selectedIndex + 1} / ${triageQueue.length}` : '0 / 0'}
              </span>
              <button
                onClick={handleNext}
                disabled={!triageQueue || selectedIndex >= triageQueue.length - 1 || loading}
                className="p-1.5 rounded hover:bg-card disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Next (Arrow Down or J)"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Keyboard Help Toggle */}
            <button
              onClick={() => setShowKeyboardHelp(!showKeyboardHelp)}
              className="p-2 rounded-lg bg-surface border border-neutral-1 hover:bg-card transition-colors"
              title="Keyboard Shortcuts (?)"
            >
              <Keyboard className="w-4 h-4" />
            </button>

            {/* Refresh */}
            <button
              onClick={() => refetch()}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-surface border border-neutral-1 rounded-lg text-text-primary hover:bg-card transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="m-4 p-4 bg-danger/10 border border-danger/20 rounded-lg">
          <p className="text-danger text-sm">Error loading triage queue: {error}</p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-3 py-1 text-sm bg-danger text-white rounded hover:bg-danger/90"
          >
            Retry
          </button>
        </div>
      )}

      {/* Keyboard Shortcuts Help */}
      {showKeyboardHelp && (
        <div className="m-4 p-4 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-text-primary flex items-center gap-2">
              <Keyboard className="w-4 h-4" />
              Keyboard Shortcuts
            </h3>
            <button
              type="button"
              onClick={() => setShowKeyboardHelp(false)}
              className="p-1 rounded hover:bg-card"
              aria-label="Close keyboard shortcuts"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <kbd className="px-2 py-1 bg-surface rounded border border-neutral-1">K</kbd>
              <span className="text-text-muted">Keep / Add to Watchlist</span>
            </div>
            <div className="flex items-center gap-2">
              <kbd className="px-2 py-1 bg-surface rounded border border-neutral-1">D</kbd>
              <span className="text-text-muted">Dismiss / Reject</span>
            </div>
            <div className="flex items-center gap-2">
              <kbd className="px-2 py-1 bg-surface rounded border border-neutral-1">J / Down</kbd>
              <span className="text-text-muted">Next Item</span>
            </div>
            <div className="flex items-center gap-2">
              <kbd className="px-2 py-1 bg-surface rounded border border-neutral-1">N / Up</kbd>
              <span className="text-text-muted">Previous Item</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content - Split View */}
      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        {/* Queue List (Left Side) */}
        <div className="w-1/3 flex flex-col bg-surface rounded-lg border border-neutral-1 overflow-hidden">
          <div className="p-3 border-b border-neutral-1 bg-card">
            <h3 className="font-semibold text-text-primary">Priority Queue</h3>
            <p className="text-xs text-text-muted">Sorted by investment potential</p>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {loading ? (
              Array(5).fill(0).map((_, i) => (
                <div key={i} className="animate-pulse p-4 bg-card rounded-lg border border-neutral-1">
                  <div className="h-4 bg-surface rounded w-20 mb-2"></div>
                  <div className="h-3 bg-surface rounded w-full mb-1"></div>
                  <div className="h-3 bg-surface rounded w-2/3"></div>
                </div>
              ))
            ) : triageQueue && triageQueue.length > 0 ? (
              triageQueue.map((suggestion, index) => (
                <TriageCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  isSelected={index === selectedIndex}
                  onSelect={() => setSelectedIndex(index)}
                  index={index}
                />
              ))
            ) : (
              <div className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-success mx-auto mb-4" />
                <h3 className="text-lg font-medium text-text-primary mb-2">Queue Empty</h3>
                <p className="text-text-muted text-sm">
                  All properties have been reviewed. Check back later for new opportunities.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Property Details (Right Side) */}
        <div className="flex-1">
          <PropertyDetailPanel
            suggestion={selectedSuggestion}
            property={selectedProperty}
            isLoading={propertyLoading}
            onKeep={handleKeep}
            onReject={handleReject}
            onViewOnMap={handleViewOnMap}
            actionLoading={actionLoading}
          />
        </div>
      </div>

      {/* Footer with Progress */}
      <div className="p-2 border-t border-neutral-1 bg-surface text-xs text-text-muted flex items-center justify-between">
        <div>
          {triageQueue?.length || 0} properties awaiting review
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <ArrowUp className="w-3 h-3" /> <ArrowDown className="w-3 h-3" /> Navigate
          </span>
          <span>Press ? for keyboard shortcuts</span>
        </div>
      </div>
    </div>
  )
}
