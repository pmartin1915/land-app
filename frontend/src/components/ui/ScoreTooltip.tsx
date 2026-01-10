import React from 'react'
import { Tooltip } from './Tooltip'

/** Score range definition with label and color */
interface ScoreRange {
  label: string
  range: string
  color: string
}

/** Score explanation configuration */
interface ScoreExplanation {
  title: string
  description: string
  ranges: ScoreRange[]
  tip?: string
}

/** Available score types */
export type ScoreType =
  | 'investment_score'
  | 'buy_hold_score'
  | 'wholesale_score'
  | 'water_score'
  | 'effective_cost'
  | 'county_market_score'
  | 'geographic_score'
  | 'total_description_score'
  | 'road_access_score'
  | 'investment_grade'

/** Pre-configured explanations for all score types */
const SCORE_EXPLANATIONS: Record<ScoreType, ScoreExplanation> = {
  investment_score: {
    title: 'Investment Score',
    description: 'Overall investment potential combining multiple factors including price, acreage, water features, and market conditions.',
    ranges: [
      { label: 'Excellent', range: '80+', color: 'text-success' },
      { label: 'Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'Fair', range: '40-59', color: 'text-warning' },
      { label: 'Poor', range: '<40', color: 'text-danger' },
    ],
  },
  buy_hold_score: {
    title: 'Buy & Hold Score',
    description: 'Time-adjusted score for long-term investment. Accounts for redemption periods and quiet title costs. Arkansas scores highest due to 30-day redemption.',
    ranges: [
      { label: 'Excellent', range: '80+', color: 'text-success' },
      { label: 'Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'Fair', range: '40-59', color: 'text-warning' },
      { label: 'Poor', range: '<40', color: 'text-danger' },
    ],
    tip: 'Arkansas properties score 100% of base score. Alabama scores ~18% due to 4-year redemption.',
  },
  wholesale_score: {
    title: 'Wholesale Score',
    description: 'Viability for quick resale. Requires tax deed (not lien), known market value, and minimum $3,000 spread or 40% margin.',
    ranges: [
      { label: 'Excellent', range: '80+', color: 'text-success' },
      { label: 'Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'Fair', range: '40-59', color: 'text-warning' },
      { label: 'Poor', range: '<40', color: 'text-danger' },
    ],
    tip: 'Tax liens score 0 - cannot easily flip debt certificates.',
  },
  water_score: {
    title: 'Water Score',
    description: 'Indicates water features detected in property description (creek, pond, river, lake access).',
    ranges: [
      { label: 'Premium', range: '10+', color: 'text-success' },
      { label: 'Good', range: '5-9', color: 'text-accent-primary' },
      { label: 'Some', range: '1-4', color: 'text-warning' },
      { label: 'None', range: '0', color: 'text-text-muted' },
    ],
    tip: 'Water features significantly increase land value and desirability.',
  },
  effective_cost: {
    title: 'Effective Cost',
    description: 'Total estimated cost including bid amount + quiet title fees + 10% buffer for recording fees and deed prep.',
    ranges: [],
    tip: 'Quiet title costs: AR $1,500 | TX $2,000 | AL $4,000 | FL $1,500',
  },
  county_market_score: {
    title: 'County Market Score',
    description: 'Evaluates county-level market conditions including property activity, price trends, and investor interest.',
    ranges: [
      { label: 'Hot Market', range: '80+', color: 'text-success' },
      { label: 'Active', range: '60-79', color: 'text-accent-primary' },
      { label: 'Moderate', range: '40-59', color: 'text-warning' },
      { label: 'Slow', range: '<40', color: 'text-danger' },
    ],
  },
  geographic_score: {
    title: 'Geographic Score',
    description: 'Location-based advantages including proximity to cities, amenities, and infrastructure.',
    ranges: [
      { label: 'Prime', range: '80+', color: 'text-success' },
      { label: 'Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'Average', range: '40-59', color: 'text-warning' },
      { label: 'Remote', range: '<40', color: 'text-danger' },
    ],
  },
  total_description_score: {
    title: 'Description Score',
    description: 'Composite score from property description analysis including lot shape, road access, and special features.',
    ranges: [
      { label: 'Excellent', range: '80+', color: 'text-success' },
      { label: 'Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'Fair', range: '40-59', color: 'text-warning' },
      { label: 'Limited', range: '<40', color: 'text-danger' },
    ],
  },
  road_access_score: {
    title: 'Road Access Score',
    description: 'Quality of road access to the property. Paved roads score highest, followed by gravel and dirt roads.',
    ranges: [
      { label: 'Paved', range: '80+', color: 'text-success' },
      { label: 'Gravel', range: '60-79', color: 'text-accent-primary' },
      { label: 'Dirt', range: '40-59', color: 'text-warning' },
      { label: 'None/Unknown', range: '<40', color: 'text-danger' },
    ],
  },
  investment_grade: {
    title: 'Investment Grade',
    description: 'Letter grade based on buy & hold score. Quick visual indicator of investment quality.',
    ranges: [
      { label: 'A - Excellent', range: '80+', color: 'text-success' },
      { label: 'B - Good', range: '60-79', color: 'text-accent-primary' },
      { label: 'C - Fair', range: '40-59', color: 'text-warning' },
      { label: 'D - Poor', range: '<40', color: 'text-danger' },
    ],
    tip: 'For beginners with limited capital, focus on B or better in Arkansas.',
  },
}

export interface ScoreTooltipProps {
  /** The type of score to explain */
  scoreType: ScoreType
  /** Additional className for the tooltip container */
  className?: string
  /** Size of the help icon */
  iconSize?: number
  /** Position of the tooltip */
  position?: 'top' | 'bottom' | 'left' | 'right'
}

/**
 * Pre-configured tooltip for explaining score types.
 * Provides consistent explanations across the app.
 */
export function ScoreTooltip({
  scoreType,
  className = '',
  iconSize = 14,
  position = 'top',
}: ScoreTooltipProps) {
  const explanation = SCORE_EXPLANATIONS[scoreType]

  if (!explanation) {
    return null
  }

  const content = (
    <div className="space-y-2">
      <div className="font-semibold text-text-primary">{explanation.title}</div>
      <p className="text-text-muted text-xs leading-relaxed">{explanation.description}</p>

      {explanation.ranges.length > 0 && (
        <div className="space-y-1 pt-1 border-t border-neutral-1">
          {explanation.ranges.map((range) => (
            <div key={range.label} className="flex items-center justify-between text-xs">
              <span className={range.color}>{range.label}</span>
              <span className="text-text-muted">{range.range}</span>
            </div>
          ))}
        </div>
      )}

      {explanation.tip && (
        <p className="text-xs text-accent-primary italic pt-1 border-t border-neutral-1">
          {explanation.tip}
        </p>
      )}
    </div>
  )

  return (
    <Tooltip
      content={content}
      showHelpIcon
      position={position}
      className={className}
      iconSize={iconSize}
    />
  )
}

export default ScoreTooltip
