import React from 'react'
import {
  usePortfolioSummary,
  usePortfolioGeographic,
  usePortfolioScores,
  usePortfolioRisk,
  usePortfolioPerformance,
} from '../lib/hooks'
import { PortfolioSummaryCards, PortfolioCharts, PortfolioRiskSection } from '../components/portfolio'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorState } from '../components/ui/ErrorState'

export function Portfolio() {
  // Fetch all portfolio data in parallel
  const { data: summary, isLoading: summaryLoading, error: summaryError } = usePortfolioSummary()
  const { data: geographic, isLoading: geoLoading, error: geoError, refetch: refetchGeo } = usePortfolioGeographic()
  const { data: scores, isLoading: scoresLoading, error: scoresError, refetch: refetchScores } = usePortfolioScores()
  const { data: risk, isLoading: riskLoading, error: riskError, refetch: refetchRisk } = usePortfolioRisk()
  const { data: performance, isLoading: perfLoading, error: perfError, refetch: refetchPerf } = usePortfolioPerformance()

  // Combined loading state for skeleton display
  const isLoadingCharts = geoLoading || scoresLoading || perfLoading
  const isLoadingRisk = riskLoading || perfLoading

  // Handle error state
  if (summaryError) {
    return (
      <div className="p-6 h-full overflow-y-auto">
        <ErrorState
          error={summaryError}
          onRetry={() => window.location.reload()}
        />
      </div>
    )
  }

  // Handle empty watchlist
  if (!summaryLoading && summary?.total_count === 0) {
    return (
      <div className="p-6 h-full overflow-y-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-primary mb-2">Portfolio Analytics</h1>
          <p className="text-text-muted">Aggregate analysis of your watched properties</p>
        </div>
        <EmptyState
          title="No Watched Properties"
          description="Add properties to your watchlist to see portfolio analytics. Star properties while browsing parcels to track them here."
          actionLabel="Browse Parcels"
          onAction={() => { window.location.href = '/parcels' }}
        />
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Portfolio Analytics</h1>
        <p className="text-text-muted">Aggregate analysis of your watched properties</p>
      </div>

      {/* Summary Cards */}
      <PortfolioSummaryCards summary={summary} isLoading={summaryLoading} />

      {/* Charts Grid */}
      <PortfolioCharts
        geographic={geographic}
        scores={scores}
        performance={performance}
        isLoading={isLoadingCharts}
        errors={{ geographic: geoError, scores: scoresError, performance: perfError }}
        onRetry={() => { refetchGeo(); refetchScores(); refetchPerf() }}
      />

      {/* Risk & Performance Section */}
      <PortfolioRiskSection
        risk={risk}
        performance={performance}
        isLoading={isLoadingRisk}
        errors={{ risk: riskError, performance: perfError }}
        onRetry={() => { refetchRisk(); refetchPerf() }}
      />
    </div>
  )
}
