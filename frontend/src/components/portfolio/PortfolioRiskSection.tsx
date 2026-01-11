import React from 'react'
import { RiskAnalysisResponse, PerformanceTrackingResponse } from '../../types/portfolio'

interface PortfolioRiskSectionProps {
  risk: RiskAnalysisResponse | null
  performance: PerformanceTrackingResponse | null
  isLoading: boolean
}

function RiskSkeleton() {
  return (
    <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
      <div className="animate-pulse">
        <div className="h-6 bg-surface rounded mb-4 w-1/4"></div>
        <div className="grid grid-cols-2 gap-4">
          <div className="h-20 bg-surface rounded"></div>
          <div className="h-20 bg-surface rounded"></div>
        </div>
      </div>
    </div>
  )
}

function RiskLevelBadge({ level }: { level: string }) {
  const config = {
    low: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
    medium: { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/20' },
    high: { bg: 'bg-orange-500/10', text: 'text-orange-500', border: 'border-orange-500/20' },
    critical: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/20' },
  }

  const { bg, text, border } = config[level as keyof typeof config] || config.medium

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${bg} ${text} border ${border}`}>
      {level.charAt(0).toUpperCase() + level.slice(1)} Risk
    </span>
  )
}

function MetricCard({ label, value, subtitle }: { label: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-surface rounded-lg p-4">
      <p className="text-sm text-text-muted mb-1">{label}</p>
      <p className="text-xl font-bold text-text-primary">{value}</p>
      {subtitle && <p className="text-xs text-text-muted mt-1">{subtitle}</p>}
    </div>
  )
}

function RiskFlag({ flag }: { flag: string }) {
  return (
    <div className="flex items-start gap-2 p-3 bg-warning/10 rounded-lg border border-warning/20">
      <svg className="w-4 h-4 text-warning mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span className="text-sm text-warning">{flag}</span>
    </div>
  )
}

export function PortfolioRiskSection({ risk, performance, isLoading }: PortfolioRiskSectionProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RiskSkeleton />
        <RiskSkeleton />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Risk Analysis */}
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">Risk Analysis</h3>
          {risk && <RiskLevelBadge level={risk.overall_risk_level} />}
        </div>

        {risk ? (
          <>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <MetricCard
                label="Diversification Score"
                value={risk.concentration.diversification_score.toFixed(0)}
                subtitle="0-100 scale"
              />
              <MetricCard
                label="Top State Concentration"
                value={`${risk.concentration.highest_state_concentration.toFixed(1)}%`}
                subtitle={risk.concentration.highest_state || 'N/A'}
              />
              <MetricCard
                label="Top County Concentration"
                value={`${risk.concentration.highest_county_concentration.toFixed(1)}%`}
                subtitle={risk.concentration.highest_county || 'N/A'}
              />
              <MetricCard
                label="Top 3 Properties"
                value={`${risk.top_3_properties_pct.toFixed(1)}%`}
                subtitle="of portfolio value"
              />
            </div>

            {/* Risk Flags */}
            {risk.risk_flags.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-text-muted mb-2">Risk Flags</p>
                {risk.risk_flags.map((flag) => (
                  <RiskFlag key={flag} flag={flag} />
                ))}
              </div>
            )}

            {risk.risk_flags.length === 0 && (
              <div className="p-4 bg-success/10 rounded-lg border border-success/20">
                <p className="text-sm text-success">No active risk flags. Portfolio looks healthy.</p>
              </div>
            )}
          </>
        ) : (
          <div className="h-40 flex items-center justify-center text-text-muted">
            No risk data available
          </div>
        )}
      </div>

      {/* Performance Summary */}
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Performance</h3>

        {performance ? (
          <>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <MetricCard
                label="Added (7 days)"
                value={performance.additions_last_7_days}
              />
              <MetricCard
                label="Added (30 days)"
                value={performance.additions_last_30_days}
              />
              <MetricCard
                label="Rated Properties"
                value={performance.rated_count}
                subtitle={`${performance.unrated_count} unrated`}
              />
              <MetricCard
                label="Avg Star Rating"
                value={performance.avg_star_rating?.toFixed(1) ?? '-'}
                subtitle="out of 5"
              />
            </div>

            {/* First Deal Status */}
            {performance.has_first_deal && (
              <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
                <p className="text-sm font-medium text-primary mb-1">First Deal In Progress</p>
                <p className="text-xs text-text-muted">
                  Stage: {performance.first_deal_stage?.replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </p>
              </div>
            )}

            {/* Star Rating Breakdown */}
            {performance.star_rating_breakdown.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-text-muted mb-2">Rating Distribution</p>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map(star => {
                    const bucket = performance.star_rating_breakdown.find(b => b.rating === star)
                    const count = bucket?.count ?? 0
                    return (
                      <div key={star} className="flex-1 text-center">
                        <div className="text-xs text-text-muted mb-1">{star}</div>
                        <div className="h-8 bg-surface rounded flex items-end justify-center">
                          <div
                            className="w-full bg-primary rounded-t"
                            style={{
                              height: `${Math.max(4, (count / Math.max(...performance.star_rating_breakdown.map(b => b.count), 1)) * 100)}%`
                            }}
                          />
                        </div>
                        <div className="text-xs text-text-muted mt-1">{count}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="h-40 flex items-center justify-center text-text-muted">
            No performance data available
          </div>
        )}
      </div>
    </div>
  )
}
