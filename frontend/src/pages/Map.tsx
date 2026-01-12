import React, { useState, useCallback } from 'react'
import { PropertyMap } from '../components/PropertyMap'
import { PropertyDetailSlideOver } from '../components/PropertyDetailSlideOver'
import { useMapProperties } from '../lib/hooks'
import { Property, PropertyFilters } from '../types'

export function Map() {
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [showFloodZones, setShowFloodZones] = useState(false) // Disabled by default - FEMA server has issues
  const [minScore, setMinScore] = useState<number | undefined>(50)
  const [filters] = useState<PropertyFilters>({})

  // Fetch properties for the map
  const { data: properties, isLoading: loading, error, refetch } = useMapProperties(filters, minScore)

  // Handle property selection
  const handlePropertySelect = useCallback((property: Property | null) => {
    setSelectedProperty(property)
  }, [])

  // Handle filter changes
  const handleScoreFilterChange = (value: number | undefined) => {
    setMinScore(value)
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-neutral-1 bg-card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-primary">Property Map</h1>
            <p className="text-sm text-text-muted">
              Spatial view with FEMA flood zones and property clustering
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Score Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-text-muted">Min Score:</label>
              <select
                value={minScore ?? 'all'}
                onChange={(e) => handleScoreFilterChange(
                  e.target.value === 'all' ? undefined : parseInt(e.target.value)
                )}
                className="px-3 py-1.5 text-sm bg-surface border border-neutral-1 rounded-lg text-text-primary focus:ring-2 focus:ring-accent-primary focus:border-transparent"
              >
                <option value="all">All Properties</option>
                <option value="85">Elite (85+)</option>
                <option value="70">Good (70+)</option>
                <option value="50">Moderate (50+)</option>
              </select>
            </div>

            {/* Flood Zone Toggle - currently disabled due to FEMA server issues */}
            <label className="flex items-center gap-2 cursor-pointer opacity-50" title="FEMA flood zone overlay temporarily disabled due to server performance issues">
              <input
                type="checkbox"
                checked={showFloodZones}
                onChange={(e) => setShowFloodZones(e.target.checked)}
                className="rounded border-neutral-2 text-accent-primary focus:ring-accent-primary"
                disabled
              />
              <span className="text-sm text-text-primary">FEMA Flood Zones (unavailable)</span>
            </label>

            {/* Refresh Button */}
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
          <p className="text-danger text-sm">Error loading properties: {error}</p>
          <button
            onClick={() => refetch()}
            className="mt-2 px-3 py-1 text-sm bg-danger text-white rounded hover:bg-danger/90"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/50">
          <div className="bg-card p-4 rounded-lg shadow-lg border border-neutral-1">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-text-primary">Loading properties...</span>
            </div>
          </div>
        </div>
      )}

      {/* Map Container */}
      <div className="flex-1 relative">
        <PropertyMap
          properties={properties || []}
          selectedProperty={selectedProperty}
          onPropertySelect={handlePropertySelect}
          showFloodZones={showFloodZones}
          showClusters={true}
          className="h-full"
        />
      </div>

      {/* Property Detail Slide-Over */}
      {selectedProperty && (
        <PropertyDetailSlideOver
          property={selectedProperty}
          isOpen={!!selectedProperty}
          onClose={() => setSelectedProperty(null)}
        />
      )}

      {/* Stats Footer */}
      <div className="p-2 border-t border-neutral-1 bg-surface text-xs text-text-muted flex items-center justify-between">
        <div>
          {properties?.length || 0} properties displayed
          {minScore && ` (score >= ${minScore})`}
        </div>
        <div className="flex items-center gap-4">
          <span>Data source: Alabama Department of Revenue</span>
        </div>
      </div>
    </div>
  )
}
