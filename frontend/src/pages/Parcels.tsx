import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Property } from '../types'
import { PropertiesTable } from '../components/PropertiesTable'
import { PropertyDetailSlideOver } from '../components/PropertyDetailSlideOver'

export function Parcels() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [slideOverOpen, setSlideOverOpen] = useState(false)

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

      {/* Properties Table */}
      <div className="flex-1 min-h-0">
        <PropertiesTable onRowSelect={handlePropertySelect} />
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