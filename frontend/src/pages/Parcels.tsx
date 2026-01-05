import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Property, PropertyFilters } from '../types'
import { PropertiesTable } from '../components/PropertiesTable'
import { PropertyDetailSlideOver } from '../components/PropertyDetailSlideOver'

const STATE_OPTIONS = [
  { value: '', label: 'All States' },
  { value: 'AL', label: 'Alabama' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'TX', label: 'Texas' },
  { value: 'FL', label: 'Florida' },
]

export function Parcels() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [slideOverOpen, setSlideOverOpen] = useState(false)
  const [filters, setFilters] = useState<PropertyFilters>({})

  // Handle state filter change
  const handleStateChange = (state: string) => {
    setFilters(prev => ({
      ...prev,
      state: state || undefined
    }))
  }

  // Handle property selection from table
  const handlePropertySelect = (property: Property | null) => {
    setSelectedProperty(property)
    setSlideOverOpen(!!property)

    // Update URL with selected property ID
    if (property) {
      setSearchParams({ selected: property.id })
    } else {
      setSearchParams({})
    }
  }

  // Close slide over
  const handleCloseSlideOver = () => {
    setSlideOverOpen(false)
    setSelectedProperty(null)
    setSearchParams({})
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Parcels</h1>
        <p className="text-text-muted">Primary work area - List + Detail</p>
      </div>

      {/* Filter Bar */}
      <div className="mb-4 flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-text-primary">State:</label>
          <select
            value={filters.state || ''}
            onChange={(e) => handleStateChange(e.target.value)}
            className="px-3 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary"
          >
            {STATE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Properties Table */}
      <div className="flex-1 min-h-0">
        <PropertiesTable onRowSelect={handlePropertySelect} globalFilters={filters} />
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
