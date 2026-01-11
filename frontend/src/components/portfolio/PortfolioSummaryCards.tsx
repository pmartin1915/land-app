import React, { memo } from 'react'
import { PortfolioSummaryResponse } from '../../types/portfolio'

interface PortfolioSummaryCardsProps {
  summary: PortfolioSummaryResponse | null
  isLoading: boolean
}

// Format currency
function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

// Format percentage
function formatPercent(value: number | null): string {
  if (value === null) return '-'
  return `${value.toFixed(1)}%`
}

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  isLoading?: boolean
}

const KPICard = memo(function KPICard({ title, value, subtitle, isLoading }: KPICardProps) {
  if (isLoading) {
    return (
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
        <div className="animate-pulse">
          <div className="h-4 bg-surface rounded mb-2 w-2/3"></div>
          <div className="h-8 bg-surface rounded mb-2 w-1/2"></div>
          <div className="h-3 bg-surface rounded w-1/3"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card hover:shadow-elevated transition-shadow duration-200">
      <h3 className="text-sm font-medium text-text-muted mb-2">{title}</h3>
      <p className="text-2xl font-bold text-text-primary">{value}</p>
      {subtitle && (
        <p className="mt-2 text-xs text-text-muted">{subtitle}</p>
      )}
    </div>
  )
})

export function PortfolioSummaryCards({ summary, isLoading }: PortfolioSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      <KPICard
        title="Total Properties"
        value={isLoading ? '' : (summary?.total_count ?? 0)}
        subtitle={isLoading ? undefined : `${summary?.total_acreage?.toFixed(1) ?? 0} total acres`}
        isLoading={isLoading}
      />
      <KPICard
        title="Portfolio Value"
        value={isLoading ? '' : formatCurrency(summary?.total_value ?? 0)}
        subtitle={isLoading ? undefined : `${formatCurrency(summary?.avg_price_per_acre ?? 0)}/acre avg`}
        isLoading={isLoading}
      />
      <KPICard
        title="Avg Investment Score"
        value={isLoading ? '' : (summary?.avg_investment_score?.toFixed(1) ?? '-')}
        subtitle={isLoading ? undefined : `${summary?.properties_with_water ?? 0} with water access`}
        isLoading={isLoading}
      />
      <KPICard
        title="Capital Utilization"
        value={isLoading ? '' : formatPercent(summary?.capital_utilization_pct ?? null)}
        subtitle={isLoading ? undefined : (summary?.capital_remaining
          ? `${formatCurrency(summary.capital_remaining)} remaining`
          : 'Set budget in settings')}
        isLoading={isLoading}
      />
    </div>
  )
}
