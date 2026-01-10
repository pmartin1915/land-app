import React, { memo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTopPicks } from '../lib/hooks'
import { Property } from '../types'
import { InvestmentGradeBadge } from './ui/InvestmentGradeBadge'
import { Tooltip } from './ui/Tooltip'
import { Info, TrendingUp, Clock, DollarSign, ExternalLink } from 'lucide-react'

export interface TopPicksCardProps {
  /** Maximum budget for effective cost filter */
  maxBudget?: number
  /** Maximum number of properties to display */
  maxItems?: number
  /** Callback when a property is clicked */
  onPropertyClick?: (property: Property) => void
}

/** Why Arkansas explanation content */
const WhyArkansasContent = () => (
  <div className="space-y-2 text-xs">
    <p className="font-semibold text-text-primary">Why Arkansas is recommended for beginners:</p>
    <ul className="space-y-1 text-text-muted">
      <li className="flex items-start gap-2">
        <Clock className="w-3 h-3 mt-0.5 text-success flex-shrink-0" />
        <span><strong>30-day redemption</strong> - Fastest path to ownership (vs 4 years for Alabama)</span>
      </li>
      <li className="flex items-start gap-2">
        <DollarSign className="w-3 h-3 mt-0.5 text-success flex-shrink-0" />
        <span><strong>$1,500 quiet title</strong> - Lowest legal cost (vs $4,000 for Alabama)</span>
      </li>
      <li className="flex items-start gap-2">
        <TrendingUp className="w-3 h-3 mt-0.5 text-success flex-shrink-0" />
        <span><strong>Warranty deed</strong> - Direct deed from state, clean title</span>
      </li>
    </ul>
  </div>
)

/** Help tooltip content for the card header */
const TopPicksHelpContent = () => (
  <div className="space-y-2 text-xs">
    <p className="text-text-muted">
      Top Picks shows the highest-scoring Arkansas properties within your budget.
    </p>
    <p className="text-text-muted">
      Properties are sorted by <strong>Buy & Hold Score</strong>, which accounts for:
    </p>
    <ul className="list-disc pl-4 text-text-muted space-y-0.5">
      <li>Acreage utility (2-10 acres ideal)</li>
      <li>Water features value</li>
      <li>Price per acre efficiency</li>
      <li>Time to ownership</li>
    </ul>
  </div>
)

/**
 * TopPicksCard - Dashboard card showing beginner-friendly property picks.
 * Filters for Arkansas properties under the user's budget.
 */
export const TopPicksCard = memo(function TopPicksCard({
  maxBudget = 8000,
  maxItems = 5,
  onPropertyClick,
}: TopPicksCardProps) {
  const navigate = useNavigate()
  const { data, isLoading, error, refetch } = useTopPicks({
    state: 'AR',
    maxEffectiveCost: maxBudget,
    limit: maxItems,
  })

  const properties = data?.items || []

  // Handle row click - navigate to property or call callback
  const handlePropertyClick = (property: Property) => {
    if (onPropertyClick) {
      onPropertyClick(property)
    } else {
      // Navigate to parcels page with this property selected
      navigate(`/parcels?selected=${property.id}`)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
        <div className="animate-pulse">
          <div className="h-6 bg-surface rounded mb-4 w-2/3"></div>
          <div className="h-4 bg-surface rounded mb-6 w-1/2"></div>
          <div className="space-y-3">
            {Array(3).fill(0).map((_, i) => (
              <div key={i} className="h-12 bg-surface rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-card rounded-lg p-6 border border-danger/30 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Top Picks for Beginners</h2>
        </div>
        <p className="text-danger text-sm mb-4">{error}</p>
        <button
          onClick={refetch}
          className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 text-sm"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-lg p-6 border border-success/30 shadow-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-success" />
          <h2 className="text-lg font-semibold text-text-primary">Top Picks for Beginners</h2>
          <Tooltip content={<TopPicksHelpContent />} showHelpIcon iconSize={16} position="right" />
        </div>
        <span className="text-xs text-text-muted bg-surface px-2 py-1 rounded">
          AR Only
        </span>
      </div>
      <p className="text-sm text-text-muted mb-4">
        Arkansas properties under ${maxBudget.toLocaleString()} total cost
      </p>

      {/* Properties Table */}
      {properties.length === 0 ? (
        <div className="text-center py-6">
          <p className="text-text-muted text-sm">No properties found under ${maxBudget.toLocaleString()}</p>
          <p className="text-text-muted text-xs mt-1">Try increasing your budget or check back later</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-1">
                <th className="text-left py-2 px-2 text-text-muted font-medium">County</th>
                <th className="text-right py-2 px-2 text-text-muted font-medium">Acres</th>
                <th className="text-right py-2 px-2 text-text-muted font-medium">Bid</th>
                <th className="text-right py-2 px-2 text-text-muted font-medium">Total Cost</th>
                <th className="text-right py-2 px-2 text-text-muted font-medium">Score</th>
                <th className="text-center py-2 px-2 text-text-muted font-medium">Grade</th>
              </tr>
            </thead>
            <tbody>
              {properties.map((property, index) => (
                <tr
                  key={property.id}
                  className={`
                    border-b border-neutral-1 last:border-0
                    hover:bg-surface/50 cursor-pointer transition-colors
                    ${index === 0 ? 'bg-success/5' : ''}
                  `}
                  onClick={() => handlePropertyClick(property)}
                >
                  <td className="py-2 px-2">
                    <div className="flex items-center gap-1">
                      {index === 0 && (
                        <span className="text-xs bg-success/20 text-success px-1.5 py-0.5 rounded font-medium">
                          #1
                        </span>
                      )}
                      <span className="text-text-primary font-medium">
                        {property.county || 'Unknown'}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 px-2 text-right text-text-muted">
                    {property.acreage?.toFixed(1) || '-'} ac
                  </td>
                  <td className="py-2 px-2 text-right text-text-primary">
                    ${property.amount?.toLocaleString() || '-'}
                  </td>
                  <td className="py-2 px-2 text-right">
                    <span className={property.effective_cost && property.effective_cost > maxBudget ? 'text-danger' : 'text-text-primary'}>
                      ${property.effective_cost?.toLocaleString() || '-'}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-right">
                    <span className={getScoreColor(property.buy_hold_score)}>
                      {property.buy_hold_score?.toFixed(1) || '-'}
                    </span>
                  </td>
                  <td className="py-2 px-2 text-center">
                    <InvestmentGradeBadge score={property.buy_hold_score} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Why Arkansas Section */}
      <div className="mt-4 pt-4 border-t border-neutral-1">
        <div className="flex items-center gap-2 mb-2">
          <Info className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-medium text-text-primary">Why Arkansas?</span>
        </div>
        <WhyArkansasContent />
      </div>

      {/* View All Link */}
      {properties.length > 0 && (
        <div className="mt-4 pt-4 border-t border-neutral-1">
          <button
            onClick={() => navigate('/parcels?state=AR')}
            className="flex items-center gap-2 text-sm text-accent-primary hover:text-accent-primary/80 transition-colors"
          >
            <span>View all Arkansas properties</span>
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
})

/** Get color class based on score value */
function getScoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'text-text-muted'
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-accent-primary'
  if (score >= 40) return 'text-warning'
  return 'text-danger'
}

export default TopPicksCard
