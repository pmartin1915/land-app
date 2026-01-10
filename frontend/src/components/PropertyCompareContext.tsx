import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { Property } from '../types'

/** Maximum number of properties that can be compared */
const MAX_COMPARE_ITEMS = 3

interface PropertyCompareContextType {
  /** List of properties selected for comparison */
  compareList: Property[]
  /** Add or remove a property from the comparison list */
  toggleCompare: (property: Property) => void
  /** Remove a specific property from comparison */
  removeFromCompare: (propertyId: string) => void
  /** Clear all properties from comparison */
  clearCompare: () => void
  /** Check if a property is in the comparison list */
  isInCompare: (propertyId: string) => boolean
  /** Whether the comparison list is at max capacity */
  isAtLimit: boolean
  /** Whether to show the comparison modal */
  showCompareModal: boolean
  /** Toggle the comparison modal visibility */
  setShowCompareModal: (show: boolean) => void
  /** Number of properties currently selected for comparison */
  compareCount: number
}

const PropertyCompareContext = createContext<PropertyCompareContextType | null>(null)

interface PropertyCompareProviderProps {
  children: ReactNode
}

/**
 * Provider component for property comparison functionality.
 * Allows selecting up to 3 properties for side-by-side comparison.
 */
export function PropertyCompareProvider({ children }: PropertyCompareProviderProps) {
  const [compareList, setCompareList] = useState<Property[]>([])
  const [showCompareModal, setShowCompareModal] = useState(false)

  const toggleCompare = useCallback((property: Property) => {
    setCompareList(prev => {
      const exists = prev.find(p => p.id === property.id)
      if (exists) {
        // Remove if already in list
        return prev.filter(p => p.id !== property.id)
      }
      // Don't add if at limit
      if (prev.length >= MAX_COMPARE_ITEMS) {
        return prev
      }
      // Add to list
      return [...prev, property]
    })
  }, [])

  const removeFromCompare = useCallback((propertyId: string) => {
    setCompareList(prev => prev.filter(p => p.id !== propertyId))
  }, [])

  const clearCompare = useCallback(() => {
    setCompareList([])
    setShowCompareModal(false)
  }, [])

  const isInCompare = useCallback((propertyId: string) => {
    return compareList.some(p => p.id === propertyId)
  }, [compareList])

  const isAtLimit = compareList.length >= MAX_COMPARE_ITEMS
  const compareCount = compareList.length

  return (
    <PropertyCompareContext.Provider
      value={{
        compareList,
        toggleCompare,
        removeFromCompare,
        clearCompare,
        isInCompare,
        isAtLimit,
        showCompareModal,
        setShowCompareModal,
        compareCount,
      }}
    >
      {children}
    </PropertyCompareContext.Provider>
  )
}

/**
 * Hook to access the property comparison context.
 * Must be used within a PropertyCompareProvider.
 */
export function usePropertyCompare(): PropertyCompareContextType {
  const context = useContext(PropertyCompareContext)
  if (!context) {
    throw new Error('usePropertyCompare must be used within a PropertyCompareProvider')
  }
  return context
}

export default PropertyCompareContext
