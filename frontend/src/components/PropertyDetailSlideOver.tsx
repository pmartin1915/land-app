import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Star,
  MapPin,
  Download,
  DollarSign,
  Ruler,
  Award,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  TrendingUp,
  Droplets,
  Map as MapIcon,
  Building,
  Eye
} from 'lucide-react'
import { Property, AISuggestion } from '../types'
import { usePropertySuggestions, useAISuggestionMutations } from '../lib/hooks'
import { ScoreTooltip, ScoreType } from './ui/ScoreTooltip'
import { InvestmentGradeBadge } from './ui/InvestmentGradeBadge'

interface PropertyDetailSlideOverProps {
  property: Property | null
  isOpen: boolean
  onClose: () => void
}

/** Get quiet title cost by state */
function getQuietTitleCost(state: string | undefined): string {
  const costs: Record<string, number> = {
    AL: 4000,
    AR: 1500,
    TX: 2000,
    FL: 1500,
  }
  const cost = state ? costs[state] : undefined
  return cost ? cost.toLocaleString() : 'N/A'
}

interface ScoreCardProps {
  title: string
  score: number
  icon: React.ReactNode
  description?: string
  scoreType?: ScoreType
}

function ScoreCard({ title, score, icon, description, scoreType }: ScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success border-success bg-success/10'
    if (score >= 60) return 'text-accent-primary border-accent-primary bg-accent-primary/10'
    if (score >= 40) return 'text-warning border-warning bg-warning/10'
    return 'text-danger border-danger bg-danger/10'
  }

  return (
    <div className={`p-4 rounded-lg border ${getScoreColor(score)}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          {icon}
          <span className="font-medium text-sm">{title}</span>
          {scoreType && <ScoreTooltip scoreType={scoreType} iconSize={12} />}
        </div>
        <span className="text-xl font-bold">{score.toFixed(1)}</span>
      </div>
      {description && (
        <p className="text-xs opacity-80">{description}</p>
      )}
    </div>
  )
}

interface AISuggestionCardProps {
  suggestion: AISuggestion
  onApply: (id: string) => void
  onReject: (id: string, reason?: string) => void
  isLoading: boolean
}

function AISuggestionCard({ suggestion, onApply, onReject, isLoading }: AISuggestionCardProps) {
  const [showRejectReason, setShowRejectReason] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-success'
    if (confidence >= 60) return 'bg-accent-primary'
    if (confidence >= 40) return 'bg-warning'
    return 'bg-danger'
  }

  return (
    <div className="p-4 bg-surface border border-neutral-1 rounded-lg">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-warning" />
            <span className="font-medium text-text-primary capitalize">
              {suggestion.field.replace('_', ' ')}
            </span>
            <div className={`w-2 h-2 rounded-full ${getConfidenceColor(suggestion.confidence)}`} />
            <span className="text-xs text-text-muted">{suggestion.confidence}% confidence</span>
          </div>
          <p className="text-sm text-text-muted mb-2">
            Suggested: <span className="font-medium text-text-primary">{suggestion.proposed_value}</span>
          </p>
          {suggestion.reason && (
            <p className="text-xs text-text-muted">{suggestion.reason}</p>
          )}
        </div>
      </div>

      <div className="flex space-x-2">
        <button
          onClick={() => onApply(suggestion.id)}
          disabled={isLoading}
          className="flex-1 px-3 py-2 bg-success text-white text-sm rounded hover:bg-opacity-90 transition-colors disabled:opacity-50 flex items-center justify-center space-x-1"
        >
          <CheckCircle className="w-3 h-3" />
          <span>Apply</span>
        </button>

        <button
          onClick={() => setShowRejectReason(!showRejectReason)}
          disabled={isLoading}
          className="flex-1 px-3 py-2 bg-surface text-text-primary border border-neutral-1 text-sm rounded hover:bg-card transition-colors disabled:opacity-50"
        >
          Reject
        </button>
      </div>

      {showRejectReason && (
        <div className="mt-3 pt-3 border-t border-neutral-1">
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Optional reason for rejection..."
            className="w-full px-3 py-2 bg-bg border border-neutral-1 rounded text-sm text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary resize-none"
            rows={2}
          />
          <div className="flex space-x-2 mt-2">
            <button
              onClick={() => {
                onReject(suggestion.id, rejectReason)
                setRejectReason('')
                setShowRejectReason(false)
              }}
              disabled={isLoading}
              className="px-3 py-1 bg-danger text-white text-xs rounded hover:bg-opacity-90 transition-colors disabled:opacity-50"
            >
              Confirm Reject
            </button>
            <button
              onClick={() => {
                setRejectReason('')
                setShowRejectReason(false)
              }}
              className="px-3 py-1 bg-surface text-text-primary border border-neutral-1 text-xs rounded hover:bg-card transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function PropertyDetailSlideOver({ property, isOpen, onClose }: PropertyDetailSlideOverProps) {
  const [activeTab, setActiveTab] = useState('overview')

  // Fetch AI suggestions if property is selected
  const { data: suggestions, loading: suggestionsLoading, refetch: refetchSuggestions } = usePropertySuggestions(property?.id || '')
  const { applySuggestion, rejectSuggestion, loading: mutationLoading } = useAISuggestionMutations()

  // Handle suggestion actions
  const handleApplySuggestion = async (suggestionId: string) => {
    try {
      await applySuggestion(suggestionId)
      refetchSuggestions()
    } catch (error) {
      console.error('Failed to apply suggestion:', error)
    }
  }

  const handleRejectSuggestion = async (suggestionId: string, reason?: string) => {
    try {
      await rejectSuggestion(suggestionId, reason)
      refetchSuggestions()
    } catch (error) {
      console.error('Failed to reject suggestion:', error)
    }
  }

  // Reset tab when property changes
  useEffect(() => {
    if (property) {
      setActiveTab('overview')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset on property id change, not full object
  }, [property?.id])

  if (!property) return null

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Eye className="w-4 h-4" /> },
    { id: 'scores', label: 'Scores', icon: <Award className="w-4 h-4" /> },
    { id: 'ai-suggestions', label: 'AI Suggestions', icon: <AlertTriangle className="w-4 h-4" />, badge: suggestions?.length || 0 },
    { id: 'history', label: 'History', icon: <Clock className="w-4 h-4" /> },
  ]

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Slide Over Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 120 }}
            className="fixed right-0 top-0 h-full w-full max-w-2xl bg-bg border-l border-neutral-1 shadow-elevated z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-neutral-1 bg-surface">
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-text-primary">Property Details</h2>
                <p className="text-sm text-text-muted font-mono">{property.parcel_id}</p>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  className="p-2 hover:bg-card rounded transition-colors"
                  title="Add to Watchlist"
                >
                  <Star className="w-5 h-5" />
                </button>
                <button
                  className="p-2 hover:bg-card rounded transition-colors"
                  title="View on Map"
                >
                  <MapPin className="w-5 h-5" />
                </button>
                <button
                  className="p-2 hover:bg-card rounded transition-colors"
                  title="Export Details"
                >
                  <Download className="w-5 h-5" />
                </button>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-card rounded transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-neutral-1 bg-surface">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors relative ${
                    activeTab === tab.id
                      ? 'border-accent-primary text-accent-primary bg-accent-primary/5'
                      : 'border-transparent text-text-muted hover:text-text-primary hover:bg-card'
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  {tab.badge && tab.badge > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-danger text-white text-xs font-bold rounded-full flex items-center justify-center">
                      {tab.badge > 99 ? '99+' : tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'overview' && (
                <div className="p-6 space-y-6">
                  {/* Key Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-card p-4 rounded-lg border border-neutral-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <DollarSign className="w-5 h-5 text-success" />
                        <span className="text-sm font-medium text-text-muted">Amount</span>
                      </div>
                      <p className="text-xl font-bold text-text-primary">
                        ${property.amount?.toLocaleString() || 'N/A'}
                      </p>
                    </div>

                    <div className="bg-card p-4 rounded-lg border border-neutral-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <Ruler className="w-5 h-5 text-accent-primary" />
                        <span className="text-sm font-medium text-text-muted">Acreage</span>
                      </div>
                      <p className="text-xl font-bold text-text-primary">
                        {property.acreage ? `${property.acreage.toFixed(2)} ac` : 'N/A'}
                      </p>
                    </div>

                    <div className="bg-card p-4 rounded-lg border border-neutral-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <TrendingUp className="w-5 h-5 text-warning" />
                        <span className="text-sm font-medium text-text-muted">Price/Acre</span>
                      </div>
                      <p className="text-xl font-bold text-text-primary">
                        ${property.price_per_acre?.toLocaleString() || 'N/A'}
                      </p>
                    </div>
                  </div>

                  {/* Property Information */}
                  <div className="bg-card p-6 rounded-lg border border-neutral-1">
                    <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center space-x-2">
                      <Building className="w-5 h-5" />
                      <span>Property Information</span>
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-text-muted">County</label>
                        <p className="text-text-primary">{property.county || 'Unknown'}</p>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-text-muted">Owner</label>
                        <p className="text-text-primary">{property.owner_name || 'Unknown'}</p>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-text-muted">Year Sold</label>
                        <p className="text-text-primary">{property.year_sold || 'N/A'}</p>
                      </div>

                      <div>
                        <label className="text-sm font-medium text-text-muted">Assessed Value</label>
                        <p className="text-text-primary">
                          {property.assessed_value ? `$${property.assessed_value.toLocaleString()}` : 'N/A'}
                        </p>
                      </div>
                    </div>

                    {property.description && (
                      <div className="mt-4">
                        <label className="text-sm font-medium text-text-muted">Description</label>
                        <p className="text-text-primary mt-1 p-3 bg-surface rounded border border-neutral-1">
                          {property.description}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'scores' && (
                <div className="p-6 space-y-6">
                  {/* Investment Grade Banner */}
                  <div className="bg-card p-4 rounded-lg border border-neutral-1 flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium text-text-muted block mb-1">Investment Grade</span>
                      <div className="flex items-center gap-2">
                        <InvestmentGradeBadge score={property.buy_hold_score} size="lg" />
                        <span className="text-lg font-semibold text-text-primary">
                          {property.buy_hold_score ? `${property.buy_hold_score.toFixed(1)} pts` : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <ScoreTooltip scoreType="investment_grade" />
                  </div>

                  {/* Cost Breakdown */}
                  <div className="bg-card p-4 rounded-lg border border-neutral-1">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-text-primary">Estimated Total Cost</h4>
                      <ScoreTooltip scoreType="effective_cost" />
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-text-muted">Bid Amount</span>
                        <span className="text-text-primary">${property.amount?.toLocaleString() || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-muted">Quiet Title ({property.state || 'N/A'})</span>
                        <span className="text-text-muted">
                          +${getQuietTitleCost(property.state)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-text-muted">Buffer (10%)</span>
                        <span className="text-text-muted">
                          +${property.amount ? Math.round(property.amount * 0.1).toLocaleString() : 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between font-semibold pt-2 border-t border-neutral-1">
                        <span className="text-text-primary">Total</span>
                        <span className={property.effective_cost && property.effective_cost > 8000 ? 'text-danger' : 'text-success'}>
                          ${property.effective_cost?.toLocaleString() || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <ScoreCard
                      title="Buy & Hold Score"
                      score={property.buy_hold_score || 0}
                      icon={<Award className="w-4 h-4" />}
                      description="Time-adjusted investment score"
                      scoreType="buy_hold_score"
                    />

                    <ScoreCard
                      title="Investment Score"
                      score={property.investment_score || 0}
                      icon={<Award className="w-4 h-4" />}
                      description="Overall investment potential"
                      scoreType="investment_score"
                    />

                    <ScoreCard
                      title="Water Score"
                      score={property.water_score || 0}
                      icon={<Droplets className="w-4 h-4" />}
                      description="Water access and quality"
                      scoreType="water_score"
                    />

                    <ScoreCard
                      title="County Market Score"
                      score={property.county_market_score || 0}
                      icon={<TrendingUp className="w-4 h-4" />}
                      description="Local market conditions"
                      scoreType="county_market_score"
                    />

                    <ScoreCard
                      title="Geographic Score"
                      score={property.geographic_score || 0}
                      icon={<MapIcon className="w-4 h-4" />}
                      description="Location and accessibility"
                      scoreType="geographic_score"
                    />

                    <ScoreCard
                      title="Description Score"
                      score={property.total_description_score || 0}
                      icon={<FileText className="w-4 h-4" />}
                      description="Property description analysis"
                      scoreType="total_description_score"
                    />

                    <ScoreCard
                      title="Road Access Score"
                      score={property.road_access_score || 0}
                      icon={<MapPin className="w-4 h-4" />}
                      description="Road access quality"
                      scoreType="road_access_score"
                    />
                  </div>

                  {/* Score Breakdown */}
                  <div className="bg-card p-6 rounded-lg border border-neutral-1">
                    <h3 className="text-lg font-semibold text-text-primary mb-4">Score Breakdown</h3>
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm text-text-muted">Lot Dimensions</span>
                          <span className="text-sm font-medium">{property.lot_dimensions_score || 0}</span>
                        </div>
                        <div className="w-full bg-surface rounded-full h-2">
                          <div
                            className="bg-accent-primary h-2 rounded-full"
                            style={{ width: `${property.lot_dimensions_score || 0}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm text-text-muted">Shape Efficiency</span>
                          <span className="text-sm font-medium">{property.shape_efficiency_score || 0}</span>
                        </div>
                        <div className="w-full bg-surface rounded-full h-2">
                          <div
                            className="bg-accent-primary h-2 rounded-full"
                            style={{ width: `${property.shape_efficiency_score || 0}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm text-text-muted">Subdivision Quality</span>
                          <span className="text-sm font-medium">{property.subdivision_quality_score || 0}</span>
                        </div>
                        <div className="w-full bg-surface rounded-full h-2">
                          <div
                            className="bg-accent-primary h-2 rounded-full"
                            style={{ width: `${property.subdivision_quality_score || 0}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'ai-suggestions' && (
                <div className="p-6 space-y-4">
                  {suggestionsLoading ? (
                    <div className="space-y-4">
                      {Array(3).fill(0).map((_, i) => (
                        <div key={i} className="animate-pulse p-4 bg-surface border border-neutral-1 rounded-lg">
                          <div className="h-4 bg-neutral-1 rounded w-1/2 mb-2"></div>
                          <div className="h-3 bg-neutral-1 rounded w-3/4"></div>
                        </div>
                      ))}
                    </div>
                  ) : suggestions && suggestions.length > 0 ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-text-primary">AI Suggestions</h3>
                        <span className="text-sm text-text-muted">{suggestions.length} pending</span>
                      </div>

                      {suggestions.map((suggestion) => (
                        <AISuggestionCard
                          key={suggestion.id}
                          suggestion={suggestion}
                          onApply={handleApplySuggestion}
                          onReject={handleRejectSuggestion}
                          isLoading={mutationLoading}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <CheckCircle className="w-12 h-12 text-success mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-text-primary mb-2">No Suggestions</h3>
                      <p className="text-text-muted">This property looks good! No AI suggestions at this time.</p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'history' && (
                <div className="p-6">
                  <div className="text-center py-8">
                    <Clock className="w-12 h-12 text-text-muted mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-text-primary mb-2">History</h3>
                    <p className="text-text-muted">Property history and transaction data coming soon.</p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}