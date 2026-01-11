import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useComponentTheme } from '../../lib/theme-provider'
import {
  GeographicBreakdownResponse,
  ScoreDistributionResponse,
  PerformanceTrackingResponse,
} from '../../types/portfolio'

interface PortfolioChartsProps {
  geographic: GeographicBreakdownResponse | null
  scores: ScoreDistributionResponse | null
  performance: PerformanceTrackingResponse | null
  isLoading: boolean
  errors?: { geographic?: string | null; scores?: string | null; performance?: string | null }
  onRetry?: () => void
}

function ChartSkeleton({ title }: { title: string }) {
  return (
    <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
      <div className="animate-pulse">
        <div className="h-6 bg-surface rounded mb-4 w-1/3"></div>
        <div className="h-64 bg-surface rounded"></div>
      </div>
    </div>
  )
}

export function PortfolioCharts({ geographic, scores, performance, isLoading, errors, onRetry }: PortfolioChartsProps) {
  const { isDark } = useComponentTheme()

  // Chart theme colors
  const chartColors = useMemo(() => ({
    primary: '#3B82F6',
    secondary: '#10B981',
    accent: '#F59E0B',
    danger: '#EF4444',
    purple: '#8B5CF6',
    background: isDark ? '#1F2937' : '#FFFFFF',
    paper: isDark ? '#374151' : '#F9FAFB',
    text: isDark ? '#F3F4F6' : '#1F2937',
    grid: isDark ? '#4B5563' : '#E5E7EB'
  }), [isDark])

  // Default chart layout
  const defaultLayout = useMemo(() => ({
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: 'Inter, sans-serif',
      color: chartColors.text,
      size: 12
    },
    margin: { t: 40, r: 40, b: 40, l: 40 },
    showlegend: true,
    legend: {
      orientation: 'h' as const,
      x: 0,
      y: -0.15,
      font: { color: chartColors.text }
    },
  }), [chartColors])

  // Default chart config - enable toolbar for keyboard accessibility
  const defaultConfig = {
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'] as ('lasso2d' | 'select2d')[],
    responsive: true
  }

  // State Distribution Pie Chart
  const stateDistributionChart = useMemo(() => {
    if (!geographic?.states?.length) return null

    const colors = [chartColors.primary, chartColors.secondary, chartColors.accent, chartColors.purple, chartColors.danger]

    return {
      data: [{
        type: 'pie' as const,
        labels: geographic.states.map(s => s.state_name),
        values: geographic.states.map(s => s.count),
        hole: 0.4,
        marker: {
          colors: geographic.states.map((_, i) => colors[i % colors.length])
        },
        textinfo: 'label+percent' as const,
        textposition: 'outside' as const,
        hovertemplate: '<b>%{label}</b><br>Properties: %{value}<br>%{percent}<extra></extra>'
      }],
      layout: {
        ...defaultLayout,
        title: {
          text: 'State Distribution',
          font: { size: 16, color: chartColors.text }
        },
        margin: { t: 60, r: 80, b: 40, l: 80 },
      }
    }
  }, [geographic, chartColors, defaultLayout])

  // Top Counties Bar Chart
  const topCountiesChart = useMemo(() => {
    if (!geographic?.states?.length) return null

    // Flatten all counties and sort by count
    const allCounties = geographic.states
      .flatMap(s => s.counties.map(c => ({ ...c, stateName: s.state_name })))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)

    if (!allCounties.length) return null

    return {
      data: [{
        type: 'bar' as const,
        x: allCounties.map(c => `${c.county}, ${c.state}`),
        y: allCounties.map(c => c.count),
        marker: {
          color: chartColors.primary,
          opacity: 0.8
        },
        hovertemplate: '<b>%{x}</b><br>Properties: %{y}<extra></extra>'
      }],
      layout: {
        ...defaultLayout,
        title: {
          text: 'Top Counties',
          font: { size: 16, color: chartColors.text }
        },
        xaxis: {
          tickangle: -45,
          gridcolor: chartColors.grid,
          zeroline: false
        },
        yaxis: {
          title: 'Properties',
          gridcolor: chartColors.grid,
          zeroline: false
        },
        margin: { t: 40, r: 40, b: 100, l: 50 },
      }
    }
  }, [geographic, chartColors, defaultLayout])

  // Score Distribution Histogram
  const scoreDistributionChart = useMemo(() => {
    if (!scores?.investment_score_buckets?.length) return null

    const bucketColors = scores.investment_score_buckets.map(b => {
      if (b.min_score >= 80) return chartColors.secondary
      if (b.min_score >= 60) return chartColors.primary
      if (b.min_score >= 40) return chartColors.accent
      return chartColors.danger
    })

    return {
      data: [{
        type: 'bar' as const,
        x: scores.investment_score_buckets.map(b => b.range_label),
        y: scores.investment_score_buckets.map(b => b.count),
        marker: {
          color: bucketColors,
          opacity: 0.8
        },
        hovertemplate: '<b>Score %{x}</b><br>Properties: %{y}<extra></extra>'
      }],
      layout: {
        ...defaultLayout,
        title: {
          text: 'Investment Score Distribution',
          font: { size: 16, color: chartColors.text }
        },
        xaxis: {
          title: 'Score Range',
          gridcolor: chartColors.grid,
          zeroline: false
        },
        yaxis: {
          title: 'Properties',
          gridcolor: chartColors.grid,
          zeroline: false
        },
      }
    }
  }, [scores, chartColors, defaultLayout])

  // Activity Timeline
  const activityTimelineChart = useMemo(() => {
    if (!performance?.activity_by_week) return null

    const weeks = Object.keys(performance.activity_by_week).sort()
    const counts = weeks.map(w => performance.activity_by_week[w])

    if (!weeks.length) return null

    return {
      data: [{
        type: 'scatter' as const,
        mode: 'lines+markers' as const,
        x: weeks,
        y: counts,
        line: {
          color: chartColors.primary,
          width: 2
        },
        marker: {
          color: chartColors.primary,
          size: 8
        },
        hovertemplate: '<b>Week of %{x}</b><br>Additions: %{y}<extra></extra>'
      }],
      layout: {
        ...defaultLayout,
        title: {
          text: 'Weekly Activity',
          font: { size: 16, color: chartColors.text }
        },
        xaxis: {
          title: 'Week',
          gridcolor: chartColors.grid,
          zeroline: false
        },
        yaxis: {
          title: 'Properties Added',
          gridcolor: chartColors.grid,
          zeroline: false
        },
      }
    }
  }, [performance, chartColors, defaultLayout])

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ChartSkeleton title="State Distribution" />
        <ChartSkeleton title="Top Counties" />
        <ChartSkeleton title="Score Distribution" />
        <ChartSkeleton title="Weekly Activity" />
      </div>
    )
  }

  // Helper to render chart error state
  const renderChartError = (message: string) => (
    <div className="h-64 flex flex-col items-center justify-center text-danger">
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Retry
        </button>
      )}
    </div>
  )

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      {/* State Distribution */}
      <div
        className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card"
        role="region"
        aria-label="State Distribution - pie chart showing property counts by state"
      >
        {stateDistributionChart ? (
          <>
            <Plot
              data={stateDistributionChart.data}
              layout={stateDistributionChart.layout}
              config={defaultConfig}
              style={{ width: '100%', height: '300px' }}
            />
            <span className="sr-only">
              {geographic?.states?.map(s => `${s.state_name}: ${s.count} properties`).join(', ')}
            </span>
          </>
        ) : errors?.geographic ? (
          renderChartError('Failed to load geographic data')
        ) : (
          <div className="h-64 flex items-center justify-center text-text-muted">
            No geographic data available
          </div>
        )}
      </div>

      {/* Top Counties */}
      <div
        className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card"
        role="region"
        aria-label="Top Counties - bar chart showing properties by county"
      >
        {topCountiesChart ? (
          <Plot
            data={topCountiesChart.data}
            layout={topCountiesChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        ) : errors?.geographic ? (
          renderChartError('Failed to load county data')
        ) : (
          <div className="h-64 flex items-center justify-center text-text-muted">
            No county data available
          </div>
        )}
      </div>

      {/* Score Distribution */}
      <div
        className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card"
        role="region"
        aria-label="Investment Score Distribution - histogram showing score ranges"
      >
        {scoreDistributionChart ? (
          <>
            <Plot
              data={scoreDistributionChart.data}
              layout={scoreDistributionChart.layout}
              config={defaultConfig}
              style={{ width: '100%', height: '300px' }}
            />
            <span className="sr-only">
              {scores?.investment_score_buckets?.map(b => `${b.range_label}: ${b.count} properties`).join(', ')}
            </span>
          </>
        ) : errors?.scores ? (
          renderChartError('Failed to load score data')
        ) : (
          <div className="h-64 flex items-center justify-center text-text-muted">
            No score data available
          </div>
        )}
      </div>

      {/* Activity Timeline */}
      <div
        className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card"
        role="region"
        aria-label="Weekly Activity - line chart showing properties added per week"
      >
        {activityTimelineChart ? (
          <Plot
            data={activityTimelineChart.data}
            layout={activityTimelineChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        ) : errors?.performance ? (
          renderChartError('Failed to load activity data')
        ) : (
          <div className="h-64 flex items-center justify-center text-text-muted">
            No activity data available
          </div>
        )}
      </div>
    </div>
  )
}
