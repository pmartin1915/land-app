import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Trash2, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Property } from '../types'
import { usePropertyCompare } from './PropertyCompareContext'
import { InvestmentGradeBadge } from './ui/InvestmentGradeBadge'

/** Get quiet title cost by state */
function getQuietTitleCost(state: string | undefined): number {
  const costs: Record<string, number> = {
    AL: 4000,
    AR: 1500,
    TX: 2000,
    FL: 1500,
  }
  return state ? costs[state] || 0 : 0
}

/** Get redemption period by state in days */
function getRedemptionPeriod(state: string | undefined): string {
  const periods: Record<string, string> = {
    AL: '4 years',
    AR: '30 days',
    TX: '180 days',
    FL: '2 years',
  }
  return state ? periods[state] || 'N/A' : 'N/A'
}

/** Comparison row data */
interface ComparisonRow {
  label: string
  getValue: (property: Property) => string | number | null
  format?: (value: string | number | null) => string
  highlightBest?: 'high' | 'low'
}

const comparisonRows: ComparisonRow[] = [
  // Location
  { label: 'County', getValue: (p) => p.county || 'Unknown' },
  { label: 'State', getValue: (p) => p.state || 'N/A' },
  // Financial
  {
    label: 'Bid Amount',
    getValue: (p) => p.amount,
    format: (v) => v ? `$${v.toLocaleString()}` : 'N/A',
    highlightBest: 'low',
  },
  {
    label: 'Effective Cost',
    getValue: (p) => p.effective_cost,
    format: (v) => v ? `$${v.toLocaleString()}` : 'N/A',
    highlightBest: 'low',
  },
  {
    label: 'Acreage',
    getValue: (p) => p.acreage,
    format: (v) => v ? `${v.toFixed(2)} ac` : 'N/A',
    highlightBest: 'high',
  },
  {
    label: 'Price/Acre',
    getValue: (p) => p.price_per_acre,
    format: (v) => v ? `$${Math.round(v).toLocaleString()}` : 'N/A',
    highlightBest: 'low',
  },
  // Scores
  {
    label: 'Buy & Hold Score',
    getValue: (p) => p.buy_hold_score,
    format: (v) => v ? v.toFixed(1) : 'N/A',
    highlightBest: 'high',
  },
  {
    label: 'Investment Score',
    getValue: (p) => p.investment_score,
    format: (v) => v ? v.toFixed(1) : 'N/A',
    highlightBest: 'high',
  },
  {
    label: 'Water Score',
    getValue: (p) => p.water_score,
    format: (v) => v ? v.toFixed(1) : '0',
    highlightBest: 'high',
  },
  // Timeline
  {
    label: 'Redemption Period',
    getValue: (p) => getRedemptionPeriod(p.state),
  },
  {
    label: 'Quiet Title Cost',
    getValue: (p) => getQuietTitleCost(p.state),
    format: (v) => `$${v.toLocaleString()}`,
    highlightBest: 'low',
  },
]

/**
 * PropertyCompareModal - Side-by-side comparison of 2-3 properties.
 */
export function PropertyCompareModal() {
  const navigate = useNavigate()
  const {
    compareList,
    showCompareModal,
    setShowCompareModal,
    removeFromCompare,
    clearCompare,
    compareCount,
  } = usePropertyCompare()

  if (!showCompareModal || compareCount === 0) return null

  // Find best values for highlighting
  const getBestIndex = (row: ComparisonRow): number | null => {
    if (!row.highlightBest) return null

    const values = compareList.map(p => {
      const val = row.getValue(p)
      return typeof val === 'number' ? val : null
    })

    const validValues = values.filter((v): v is number => v !== null)
    if (validValues.length === 0) return null

    const bestValue = row.highlightBest === 'high'
      ? Math.max(...validValues)
      : Math.min(...validValues)

    return values.indexOf(bestValue)
  }

  return (
    <AnimatePresence>
      {showCompareModal && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowCompareModal(false)}
            className="fixed inset-0 bg-black/50 z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-4 md:inset-10 bg-bg rounded-lg shadow-elevated z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-neutral-1 bg-surface">
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Compare Properties</h2>
                <p className="text-sm text-text-muted">{compareCount} of 3 properties selected</p>
              </div>
              <button
                onClick={() => setShowCompareModal(false)}
                className="p-2 hover:bg-card rounded transition-colors"
                aria-label="Close comparison modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              <table className="w-full border-collapse">
                {/* Property Headers */}
                <thead>
                  <tr className="border-b border-neutral-1">
                    <th className="text-left py-3 px-4 w-40 text-sm font-medium text-text-muted">
                      Property
                    </th>
                    {compareList.map((property) => (
                      <th key={property.id} className="text-left py-3 px-4">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-accent-primary text-sm">
                              {property.parcel_id}
                            </span>
                            <button
                              onClick={() => removeFromCompare(property.id)}
                              className="p-1 text-danger hover:bg-danger/10 rounded transition-colors"
                              aria-label={`Remove ${property.parcel_id} from comparison`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="flex items-center gap-2">
                            <InvestmentGradeBadge score={property.buy_hold_score} size="sm" />
                            <span className="text-sm text-text-muted">
                              {property.county}, {property.state}
                            </span>
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* Comparison Rows */}
                <tbody>
                  {comparisonRows.map((row, rowIndex) => {
                    const bestIndex = getBestIndex(row)

                    return (
                      <tr
                        key={row.label}
                        className={`border-b border-neutral-1 ${rowIndex % 2 === 0 ? 'bg-surface/30' : ''}`}
                      >
                        <td className="py-3 px-4 text-sm font-medium text-text-muted">
                          {row.label}
                        </td>
                        {compareList.map((property, colIndex) => {
                          const value = row.getValue(property)
                          const displayValue = row.format
                            ? row.format(value)
                            : String(value ?? 'N/A')
                          const isBest = bestIndex === colIndex

                          return (
                            <td
                              key={property.id}
                              className={`py-3 px-4 text-sm ${
                                isBest
                                  ? 'bg-success/10 text-success font-semibold'
                                  : 'text-text-primary'
                              }`}
                            >
                              {displayValue}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-neutral-1 bg-surface">
              <button
                onClick={clearCompare}
                className="px-4 py-2 text-sm text-danger hover:bg-danger/10 rounded-lg transition-colors"
              >
                Clear All
              </button>

              <button
                onClick={() => {
                  setShowCompareModal(false)
                  navigate('/parcels')
                }}
                className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white text-sm rounded-lg hover:bg-opacity-90 transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                <span>View on Parcels</span>
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default PropertyCompareModal
