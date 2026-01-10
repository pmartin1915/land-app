import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Property } from '../types'
import { api, FirstDealStage } from '../lib/api'
import { PropertyDetailSlideOver } from '../components/PropertyDetailSlideOver'
import { InvestmentGradeBadge } from '../components/ui/InvestmentGradeBadge'
import { usePropertyCompare } from '../components/PropertyCompareContext'
import { DealPipelineVisual } from '../components/DealPipelineVisual'
import {
  getDueDiligenceLinks,
  getAttorneyLinks,
  getSellingLinks,
  type ExternalLink,
} from '../lib/external-links'
import {
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  DollarSign,
  Scale,
  TrendingUp,
  AlertTriangle,
  ExternalLink,
  Sparkles,
  Clock,
  MapPin,
  Info,
  Star,
  Loader2,
} from 'lucide-react'

interface Step {
  id: string
  title: string
  shortTitle: string
  description: string
  details: React.ReactNode
  tips: string[]
  estimatedTime?: string
  cost?: string
  externalLinks?: ExternalLink[]
}

/**
 * Renders external resource links for a step
 */
function ExternalLinksSection({ links }: { links: ExternalLink[] }) {
  if (links.length === 0) return null

  return (
    <div className="mt-4 p-3 bg-surface rounded-lg border border-neutral-1">
      <p className="text-sm font-medium text-text-primary flex items-center gap-2 mb-3">
        <ExternalLink className="w-4 h-4 text-accent-primary" />
        Helpful Resources
      </p>
      <div className="flex flex-wrap gap-2">
        {links.map(link => (
          <a
            key={link.label}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-card rounded-lg hover:bg-bg border border-neutral-1 text-text-primary hover:text-accent-primary transition-colors"
            title={link.description}
          >
            {link.label}
            <ExternalLink className="w-3 h-3" />
          </a>
        ))}
      </div>
    </div>
  )
}

const STEPS: Step[] = [
  {
    id: 'research',
    title: 'Step 1: Find Your Property',
    shortTitle: 'Research',
    description: 'Use the filters to find Arkansas properties within your budget that have good scores.',
    estimatedTime: '1-2 hours',
    details: (
      <div className="space-y-3 text-sm">
        <p>Arkansas is the best state for beginners because:</p>
        <ul className="list-disc list-inside space-y-1 text-text-muted ml-2">
          <li><strong>30-day redemption period</strong> - Previous owner has only 30 days to reclaim (vs 4 years in Alabama)</li>
          <li><strong>$1,500 quiet title cost</strong> - Much cheaper than other states ($4,000 in Alabama)</li>
          <li><strong>Clear title process</strong> - Well-established procedures</li>
        </ul>
        <div className="mt-4 p-3 bg-accent-primary/10 rounded-lg border border-accent-primary/20">
          <p className="font-medium text-accent-primary">What to look for:</p>
          <ul className="list-disc list-inside space-y-1 text-text-muted mt-2 ml-2">
            <li>Buy & Hold Score above 40 (higher is better)</li>
            <li>Total cost under your budget ($3k-$8k)</li>
            <li>At least 0.5 acres (more versatile)</li>
            <li>Avoid "landlocked" or "no access" in description</li>
          </ul>
        </div>
      </div>
    ),
    tips: [
      'Start with the "Beginner Friendly" filter on the Parcels page',
      'Compare 3-5 properties before deciding',
      'Check the property on Google Maps to see the area',
      'Higher water score = potential pond or creek (adds value)'
    ]
  },
  {
    id: 'due-diligence',
    title: 'Step 2: Research the Property',
    shortTitle: 'Due Diligence',
    description: 'Before bidding, verify key details about the property.',
    estimatedTime: '2-4 hours',
    details: (
      <div className="space-y-3 text-sm">
        <p>Free research you can do online:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted ml-2">
          <li><strong>Google Maps</strong> - Check satellite view for access roads, neighbors, terrain</li>
          <li><strong>County GIS</strong> - Verify acreage, lot lines, flood zones</li>
          <li><strong>FEMA Flood Maps</strong> - Avoid properties in high-risk flood zones</li>
          <li><strong>Zillow/Redfin</strong> - Check nearby land prices for comparison</li>
        </ul>
        <div className="mt-4 p-3 bg-warning/10 rounded-lg border border-warning/20">
          <p className="font-medium text-warning flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Red Flags to Avoid
          </p>
          <ul className="list-disc list-inside space-y-1 text-text-muted mt-2 ml-2">
            <li>No road access (landlocked)</li>
            <li>In a flood zone</li>
            <li>Very irregular shape (hard to use/sell)</li>
            <li>Near industrial sites or landfills</li>
          </ul>
        </div>
      </div>
    ),
    tips: [
      'County assessor websites have free property info',
      'Call the county office if you have questions - they are usually helpful',
      'Take screenshots of your research for your records'
    ],
    externalLinks: getDueDiligenceLinks('AR')
  },
  {
    id: 'bidding',
    title: 'Step 3: Place Your Bid',
    shortTitle: 'Bid',
    description: 'Register on the auction site and submit your bid before the deadline.',
    estimatedTime: '30 minutes',
    cost: 'Deposit may be required',
    details: (
      <div className="space-y-3 text-sm">
        <p>Arkansas uses online auctions. Here is the process:</p>
        <ol className="list-decimal list-inside space-y-2 text-text-muted ml-2">
          <li><strong>Register</strong> on the county's auction website (usually requires ID verification)</li>
          <li><strong>Deposit</strong> - Some counties require a refundable deposit to bid</li>
          <li><strong>Place bid</strong> - Enter your maximum bid amount</li>
          <li><strong>Wait</strong> - Auction closes on the listed date</li>
        </ol>
        <div className="mt-4 p-3 bg-success/10 rounded-lg border border-success/20">
          <p className="font-medium text-success">Bidding Strategy</p>
          <ul className="list-disc list-inside space-y-1 text-text-muted mt-2 ml-2">
            <li>Set your maximum bid based on total cost (bid + $1,500 quiet title)</li>
            <li>Do not get emotional - there will be other properties</li>
            <li>If you are outbid, move on to the next opportunity</li>
          </ul>
        </div>
      </div>
    ),
    tips: [
      'Create your auction account a few days before to avoid last-minute issues',
      'Double-check the property ID before bidding',
      'Set a firm maximum and stick to it'
    ]
  },
  {
    id: 'winning',
    title: 'Step 4: Win & Pay',
    shortTitle: 'Win',
    description: 'If you win, complete payment within the required timeframe.',
    estimatedTime: '1-3 days',
    cost: 'Your winning bid amount',
    details: (
      <div className="space-y-3 text-sm">
        <p>After winning:</p>
        <ol className="list-decimal list-inside space-y-2 text-text-muted ml-2">
          <li><strong>Payment deadline</strong> - Usually 24-72 hours to pay in full</li>
          <li><strong>Payment methods</strong> - Wire transfer, cashier's check, or certified funds</li>
          <li><strong>Receive deed</strong> - County issues a tax deed in your name</li>
        </ol>
        <div className="mt-4 p-3 bg-accent-primary/10 rounded-lg border border-accent-primary/20">
          <p className="font-medium text-accent-primary">Important</p>
          <p className="text-text-muted mt-1">
            The tax deed gives you ownership, but it is not "marketable title" yet.
            You will need to quiet the title (Step 5) before you can easily sell.
          </p>
        </div>
      </div>
    ),
    tips: [
      'Have funds ready before bidding',
      'Wire transfers are fastest but have fees ($25-50)',
      'Keep all payment receipts and documentation'
    ]
  },
  {
    id: 'redemption',
    title: 'Step 5: Wait for Redemption Period',
    shortTitle: 'Wait 30 Days',
    description: 'The previous owner has 30 days to "redeem" the property by paying back taxes plus penalties.',
    estimatedTime: '30 days',
    details: (
      <div className="space-y-3 text-sm">
        <p>During the redemption period:</p>
        <ul className="list-disc list-inside space-y-2 text-text-muted ml-2">
          <li><strong>You own the property</strong>, but the previous owner can reclaim it</li>
          <li><strong>If redeemed</strong> - You get your money back plus interest (usually 10-20%)</li>
          <li><strong>If not redeemed</strong> - You keep the property and proceed to quiet title</li>
        </ul>
        <div className="mt-4 p-3 bg-success/10 rounded-lg border border-success/20">
          <p className="font-medium text-success">Good News</p>
          <p className="text-text-muted mt-1">
            Redemption is rare for vacant land. Most previous owners abandoned the property
            because they could not pay taxes - they are unlikely to come up with the money now.
          </p>
        </div>
      </div>
    ),
    tips: [
      'Mark your calendar for the redemption deadline',
      'Start researching quiet title attorneys during this time',
      'Redemption is actually a win-win - you get interest on your money'
    ]
  },
  {
    id: 'quiet-title',
    title: 'Step 6: Quiet Title',
    shortTitle: 'Quiet Title',
    description: 'File a quiet title lawsuit to get "marketable title" that any buyer will accept.',
    estimatedTime: '3-6 months',
    cost: '$1,200 - $1,800 in Arkansas',
    details: (
      <div className="space-y-3 text-sm">
        <p>The quiet title process:</p>
        <ol className="list-decimal list-inside space-y-2 text-text-muted ml-2">
          <li><strong>Hire an attorney</strong> - Find one who specializes in quiet title in Arkansas</li>
          <li><strong>File lawsuit</strong> - Attorney files in the county where property is located</li>
          <li><strong>Notification</strong> - All potential claimants are notified by publication</li>
          <li><strong>Court order</strong> - Judge issues order clearing title</li>
          <li><strong>Record deed</strong> - New deed is recorded with the county</li>
        </ol>
        <div className="mt-4 p-3 bg-accent-primary/10 rounded-lg border border-accent-primary/20">
          <p className="font-medium text-accent-primary">Finding an Attorney</p>
          <p className="text-text-muted mt-1">
            Search "quiet title attorney Arkansas" or ask in land investing forums.
            Get quotes from 2-3 attorneys. Typical cost is $1,200-$1,800 for vacant land.
          </p>
        </div>
      </div>
    ),
    tips: [
      'Get attorney quotes before you bid so you know total cost',
      'Some attorneys offer flat-rate pricing for vacant land',
      'The process is mostly waiting - not much work for you'
    ],
    externalLinks: getAttorneyLinks('AR')
  },
  {
    id: 'sell-or-hold',
    title: 'Step 7: Sell or Hold',
    shortTitle: 'Exit',
    description: 'Once you have clear title, decide whether to sell for profit or hold for appreciation.',
    estimatedTime: 'Varies',
    details: (
      <div className="space-y-3 text-sm">
        <p>Your options after quiet title:</p>
        <div className="grid gap-4 mt-2">
          <div className="p-3 bg-surface rounded-lg border border-neutral-1">
            <p className="font-medium text-success">Option A: Sell</p>
            <ul className="list-disc list-inside space-y-1 text-text-muted mt-2 ml-2">
              <li>List on Facebook Marketplace, Craigslist, LandWatch</li>
              <li>Offer owner financing to get higher price</li>
              <li>Target price: 2-3x your total investment</li>
            </ul>
          </div>
          <div className="p-3 bg-surface rounded-lg border border-neutral-1">
            <p className="font-medium text-accent-primary">Option B: Hold</p>
            <ul className="list-disc list-inside space-y-1 text-text-muted mt-2 ml-2">
              <li>Pay annual property taxes (usually $20-100/year)</li>
              <li>Land tends to appreciate 3-5% annually</li>
              <li>Sell later when you need funds or market is better</li>
            </ul>
          </div>
        </div>
      </div>
    ),
    tips: [
      'Owner financing can double your profit but ties up capital longer',
      'Good photos and descriptions sell properties faster',
      'Price competitively by checking similar listings in the area'
    ],
    externalLinks: getSellingLinks('AR')
  }
]

export function MyFirstDeal() {
  const navigate = useNavigate()
  const [expandedStep, setExpandedStep] = useState<string>('research')
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [recommendedProperties, setRecommendedProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null)
  const [slideOverOpen, setSlideOverOpen] = useState(false)

  // First deal tracking state
  const [firstDealProperty, setFirstDealProperty] = useState<Property | null>(null)
  const [firstDealStage, setFirstDealStage] = useState<FirstDealStage | null>(null)
  const [isSettingFirstDeal, setIsSettingFirstDeal] = useState<string | null>(null) // property ID being set
  const [isRemovingFirstDeal, setIsRemovingFirstDeal] = useState(false)

  // Property comparison
  const { toggleCompare, isInCompare, isAtLimit, compareCount, setShowCompareModal } = usePropertyCompare()

  // Fetch first deal on mount
  useEffect(() => {
    async function fetchFirstDeal() {
      try {
        const response = await api.watchlist.getFirstDeal()
        if (response.has_first_deal && response.property) {
          setFirstDealProperty(response.property)
          setFirstDealStage(response.stage)
        }
      } catch (err) {
        console.error('Failed to fetch first deal:', err)
      }
    }
    fetchFirstDeal()
  }, [])

  // Fetch recommended properties for beginners
  useEffect(() => {
    async function fetchRecommended() {
      try {
        const response = await api.properties.getProperties({
          filters: {
            state: 'AR',
            minBuyHoldScore: 30
          },
          sort_by: 'buy_hold_score',
          sort_order: 'desc',
          per_page: 6
        })
        // Filter to $3k-$8k effective cost range
        const filtered = (response.items || []).filter(
          p => p.effective_cost && p.effective_cost >= 3000 && p.effective_cost <= 8000
        )
        setRecommendedProperties(filtered.slice(0, 5))
      } catch (err) {
        console.error('Failed to fetch recommended properties:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRecommended()
  }, [])

  // Load completed steps from localStorage (fallback for non-synced progress)
  useEffect(() => {
    const saved = localStorage.getItem('myFirstDeal_completedSteps')
    if (saved) {
      setCompletedSteps(new Set(JSON.parse(saved)))
    }
  }, [])

  // Set a property as first deal
  const handleSetFirstDeal = useCallback(async (property: Property) => {
    setIsSettingFirstDeal(property.id)
    try {
      const response = await api.watchlist.setFirstDeal(property.id)
      setFirstDealProperty(property)
      setFirstDealStage(response.stage as FirstDealStage)
    } catch (err) {
      console.error('Failed to set first deal:', err)
    } finally {
      setIsSettingFirstDeal(null)
    }
  }, [])

  // Remove first deal assignment
  const handleRemoveFirstDeal = useCallback(async () => {
    setIsRemovingFirstDeal(true)
    try {
      await api.watchlist.removeFirstDeal()
      setFirstDealProperty(null)
      setFirstDealStage(null)
    } catch (err) {
      console.error('Failed to remove first deal:', err)
    } finally {
      setIsRemovingFirstDeal(false)
    }
  }, [])

  // Update pipeline stage when clicking on a stage
  const handleStageClick = useCallback(async (stage: FirstDealStage) => {
    if (!firstDealProperty) return
    try {
      await api.watchlist.updateFirstDealStage(stage)
      setFirstDealStage(stage)
    } catch (err) {
      console.error('Failed to update stage:', err)
    }
  }, [firstDealProperty])

  const toggleStepComplete = (stepId: string) => {
    const newCompleted = new Set(completedSteps)
    if (newCompleted.has(stepId)) {
      newCompleted.delete(stepId)
    } else {
      newCompleted.add(stepId)
    }
    setCompletedSteps(newCompleted)
    localStorage.setItem('myFirstDeal_completedSteps', JSON.stringify([...newCompleted]))
  }

  const toggleExpand = (stepId: string) => {
    setExpandedStep(expandedStep === stepId ? '' : stepId)
  }

  const handlePropertyClick = (property: Property) => {
    setSelectedProperty(property)
    setSlideOverOpen(true)
  }

  const progress = (completedSteps.size / STEPS.length) * 100

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-success/20 rounded-lg">
            <Sparkles className="w-6 h-6 text-success" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">My First Deal</h1>
            <p className="text-text-muted">Your step-by-step guide to buying Arkansas tax lien property</p>
          </div>
        </div>
      </div>

      {/* Deal Pipeline Visual */}
      <DealPipelineVisual
        property={firstDealProperty}
        currentStage={firstDealStage}
        onStageClick={handleStageClick}
        onRemove={handleRemoveFirstDeal}
        isRemoving={isRemovingFirstDeal}
        className="mb-6"
      />

      {/* Progress Bar */}
      <div className="mb-8 p-4 bg-card rounded-lg border border-neutral-1">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-text-primary">Your Progress</span>
          <span className="text-sm text-text-muted">{completedSteps.size} of {STEPS.length} steps</span>
        </div>
        <div className="h-2 bg-surface rounded-full overflow-hidden">
          <div
            className="h-full bg-success transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Steps Checklist */}
        <div className="lg:col-span-2 space-y-3">
          {STEPS.map((step, index) => {
            const isCompleted = completedSteps.has(step.id)
            const isExpanded = expandedStep === step.id

            return (
              <div
                key={step.id}
                className={`bg-card rounded-lg border transition-all ${
                  isCompleted
                    ? 'border-success/30 bg-success/5'
                    : 'border-neutral-1'
                }`}
              >
                {/* Step Header */}
                <div
                  className="flex items-center gap-3 p-4 cursor-pointer"
                  onClick={() => toggleExpand(step.id)}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleStepComplete(step.id)
                    }}
                    className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isCompleted
                        ? 'bg-success border-success text-white'
                        : 'border-text-muted hover:border-success'
                    }`}
                    aria-label={isCompleted ? 'Mark as incomplete' : 'Mark as complete'}
                  >
                    {isCompleted && <CheckCircle2 className="w-4 h-4" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <h3 className={`font-medium ${isCompleted ? 'text-success' : 'text-text-primary'}`}>
                      {step.title}
                    </h3>
                    <p className="text-sm text-text-muted truncate">{step.description}</p>
                  </div>

                  <div className="flex items-center gap-2 text-text-muted">
                    {step.estimatedTime && (
                      <span className="text-xs bg-surface px-2 py-1 rounded flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {step.estimatedTime}
                      </span>
                    )}
                    {step.cost && (
                      <span className="text-xs bg-surface px-2 py-1 rounded flex items-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        {step.cost}
                      </span>
                    )}
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5" />
                    ) : (
                      <ChevronRight className="w-5 h-5" />
                    )}
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-neutral-1 mt-0">
                    <div className="pt-4">
                      {step.details}

                      {/* Tips */}
                      {step.tips.length > 0 && (
                        <div className="mt-4 p-3 bg-surface rounded-lg">
                          <p className="text-sm font-medium text-text-primary flex items-center gap-2 mb-2">
                            <Info className="w-4 h-4 text-accent-primary" />
                            Tips
                          </p>
                          <ul className="space-y-1">
                            {step.tips.map((tip, i) => (
                              <li key={i} className="text-sm text-text-muted flex items-start gap-2">
                                <span className="text-accent-primary mt-1">-</span>
                                {tip}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* External Resource Links */}
                      {step.externalLinks && step.externalLinks.length > 0 && (
                        <ExternalLinksSection links={step.externalLinks} />
                      )}

                      {/* Action Button */}
                      {step.id === 'research' && (
                        <button
                          onClick={() => navigate('/parcels')}
                          className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-colors"
                        >
                          <span>Browse Arkansas Properties</span>
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Recommended Properties Sidebar */}
        <div className="space-y-4">
          <div className="bg-card rounded-lg border border-neutral-1 p-4">
            <h3 className="font-medium text-text-primary mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-success" />
              Recommended for You
            </h3>
            <p className="text-sm text-text-muted mb-4">
              Arkansas properties in your $3k-$8k budget range, sorted by Buy & Hold score.
            </p>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-20 bg-surface rounded-lg animate-pulse" />
                ))}
              </div>
            ) : recommendedProperties.length > 0 ? (
              <div className="space-y-2">
                {recommendedProperties.map(property => {
                  const isCurrentFirstDeal = firstDealProperty?.id === property.id
                  const isSettingThis = isSettingFirstDeal === property.id

                  return (
                    <div
                      key={property.id}
                      className={`p-3 bg-surface rounded-lg hover:bg-bg transition-colors border ${
                        isCurrentFirstDeal
                          ? 'border-success/50 bg-success/5'
                          : 'border-transparent hover:border-accent-primary/30'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          onClick={() => handlePropertyClick(property)}
                          className="min-w-0 text-left flex-1"
                        >
                          <p className="font-mono text-sm text-accent-primary truncate">
                            {property.parcel_id}
                          </p>
                          <p className="text-xs text-text-muted flex items-center gap-1 mt-0.5">
                            <MapPin className="w-3 h-3" />
                            {property.county}, AR
                          </p>
                        </button>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleCompare(property)
                            }}
                            disabled={!isInCompare(property.id) && isAtLimit}
                            className={`p-1.5 rounded transition-colors ${
                              isInCompare(property.id)
                                ? 'bg-accent-primary text-white'
                                : 'hover:bg-card text-text-muted hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed'
                            }`}
                            aria-label={isInCompare(property.id) ? 'Remove from compare' : 'Add to compare'}
                            title={isAtLimit && !isInCompare(property.id) ? 'Compare limit reached (3 max)' : isInCompare(property.id) ? 'Remove from compare' : 'Add to compare'}
                          >
                            <Scale className="w-4 h-4" />
                          </button>
                          <InvestmentGradeBadge score={property.buy_hold_score} size="sm" />
                        </div>
                      </div>
                      <button
                        onClick={() => handlePropertyClick(property)}
                        className="w-full text-left"
                      >
                        <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
                          <span className="font-medium text-text-primary">
                            ${property.effective_cost?.toLocaleString() || property.amount?.toLocaleString()}
                          </span>
                          <span>{property.acreage?.toFixed(2)} ac</span>
                          {property.water_score && property.water_score > 0 && (
                            <span className="text-accent-secondary">Water</span>
                          )}
                        </div>
                      </button>

                      {/* Set as First Deal Button */}
                      {!isCurrentFirstDeal && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleSetFirstDeal(property)
                          }}
                          disabled={isSettingThis}
                          className="w-full mt-2 flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs bg-card hover:bg-accent-primary/10 border border-neutral-1 hover:border-accent-primary/30 rounded-lg transition-colors disabled:opacity-50"
                        >
                          {isSettingThis ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Setting...
                            </>
                          ) : (
                            <>
                              <Star className="w-3 h-3" />
                              Set as My First Deal
                            </>
                          )}
                        </button>
                      )}
                      {isCurrentFirstDeal && (
                        <div className="mt-2 flex items-center justify-center gap-1 text-xs text-success">
                          <CheckCircle2 className="w-3 h-3" />
                          Your First Deal
                        </div>
                      )}
                    </div>
                  )
                })}

                <button
                  onClick={() => navigate('/parcels')}
                  className="w-full mt-2 text-sm text-accent-primary hover:underline flex items-center justify-center gap-1"
                >
                  View all properties
                  <ChevronRight className="w-4 h-4" />
                </button>

                {/* Floating Compare Bar */}
                {compareCount > 0 && (
                  <div className="mt-4 p-3 bg-accent-primary/10 border border-accent-primary/30 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-text-primary">{compareCount} selected</span>
                      <button
                        onClick={() => setShowCompareModal(true)}
                        className="px-3 py-1.5 bg-accent-primary text-white text-sm rounded-lg hover:bg-opacity-90 transition-colors flex items-center gap-1"
                      >
                        <Scale className="w-3 h-3" />
                        Compare
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-text-muted text-center py-4">
                No properties found in this budget range. Try expanding your search.
              </p>
            )}
          </div>

          {/* Quick Stats */}
          <div className="bg-card rounded-lg border border-neutral-1 p-4">
            <h3 className="font-medium text-text-primary mb-3">Arkansas at a Glance</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Redemption Period</span>
                <span className="font-medium text-success">30 days</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Quiet Title Cost</span>
                <span className="font-medium text-text-primary">~$1,500</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Typical Timeline</span>
                <span className="font-medium text-text-primary">4-6 months</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Beginner Friendly</span>
                <span className="font-medium text-success">Yes</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Property Detail Slide Over */}
      <PropertyDetailSlideOver
        property={selectedProperty}
        isOpen={slideOverOpen}
        onClose={() => {
          setSlideOverOpen(false)
          setSelectedProperty(null)
        }}
      />
    </div>
  )
}
