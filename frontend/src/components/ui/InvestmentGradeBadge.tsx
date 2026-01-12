import React from 'react'
import { ScoreTooltip } from './ScoreTooltip'

export interface InvestmentGradeBadgeProps {
  /** The buy_hold_score to determine grade */
  score: number | null | undefined
  /** Size of the badge */
  size?: 'sm' | 'md' | 'lg'
  /** Show tooltip explaining the grade */
  showTooltip?: boolean
  /** Additional className */
  className?: string
}

/** Grade configuration with colors */
interface GradeConfig {
  grade: string
  color: string
  bgColor: string
  label: string
}

/**
 * Get investment grade configuration based on score.
 * A = 80+, B = 60-79, C = 40-59, D = <40
 */
function getInvestmentGrade(score: number | null | undefined): GradeConfig {
  if (score === null || score === undefined) {
    return {
      grade: '-',
      color: 'text-text-muted',
      bgColor: 'bg-neutral-1',
      label: 'No Score',
    }
  }

  if (score >= 80) {
    return {
      grade: 'A',
      color: 'text-success',
      bgColor: 'bg-success/10',
      label: 'Excellent',
    }
  }

  if (score >= 60) {
    return {
      grade: 'B',
      color: 'text-accent-primary',
      bgColor: 'bg-accent-primary/10',
      label: 'Good',
    }
  }

  if (score >= 40) {
    return {
      grade: 'C',
      color: 'text-warning',
      bgColor: 'bg-warning/10',
      label: 'Fair',
    }
  }

  return {
    grade: 'D',
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    label: 'Poor',
  }
}

/** Size configurations */
const SIZE_CLASSES = {
  sm: 'w-5 h-5 text-xs',
  md: 'w-7 h-7 text-sm',
  lg: 'w-9 h-9 text-base',
}

/**
 * Investment Grade Badge - A/B/C/D color-coded badge.
 * Based on buy_hold_score thresholds.
 */
export function InvestmentGradeBadge({
  score,
  size = 'md',
  showTooltip = false,
  className = '',
}: InvestmentGradeBadgeProps) {
  const { grade, color, bgColor, label } = getInvestmentGrade(score)

  const badge = (
    <div
      className={`
        inline-flex items-center justify-center
        rounded-md font-bold
        ${SIZE_CLASSES[size]}
        ${color}
        ${bgColor}
        ${className}
      `}
      aria-label={`Investment Grade: ${grade} (${label})`}
      title={!showTooltip ? `${grade} - ${label}` : undefined}
    >
      {grade}
    </div>
  )

  if (showTooltip) {
    return (
      <div className="inline-flex items-center gap-1">
        {badge}
        <ScoreTooltip scoreType="investment_grade" iconSize={12} />
      </div>
    )
  }

  return badge
}

/**
 * Get investment grade letter from score.
 * Useful for sorting or filtering.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getGradeLetter(score: number | null | undefined): string {
  return getInvestmentGrade(score).grade
}

/**
 * Get investment grade with full details.
 * Useful for displaying grade information.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getGradeDetails(score: number | null | undefined): GradeConfig {
  return getInvestmentGrade(score)
}

export default InvestmentGradeBadge
