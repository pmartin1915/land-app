import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useComponentTheme } from '../lib/theme-provider'

interface DashboardChartsProps {
  stats: any
  isLoading: boolean
}

export function DashboardCharts({ stats, isLoading }: DashboardChartsProps) {
  const { isDark } = useComponentTheme()

  // Chart theme colors
  const chartColors = {
    primary: '#3B82F6',
    secondary: '#10B981',
    accent: '#F59E0B',
    danger: '#EF4444',
    background: isDark ? '#1F2937' : '#FFFFFF',
    paper: isDark ? '#374151' : '#F9FAFB',
    text: isDark ? '#F3F4F6' : '#1F2937',
    grid: isDark ? '#4B5563' : '#E5E7EB'
  }

  // Default chart layout
  const defaultLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: 'Inter, sans-serif',
      color: chartColors.text,
      size: 12
    },
    margin: { t: 40, r: 40, b: 40, l: 40 },
    showlegend: false,
    xaxis: {
      gridcolor: chartColors.grid,
      zeroline: false
    },
    yaxis: {
      gridcolor: chartColors.grid,
      zeroline: false
    }
  }

  // Default chart config
  const defaultConfig = {
    displayModeBar: false,
    responsive: true
  }

  // Price Distribution Chart
  const priceDistributionChart = useMemo(() => {
    if (!stats?.price_distribution) return null

    const data = [{
      x: stats.price_distribution.ranges,
      y: stats.price_distribution.counts,
      type: 'bar' as const,
      marker: {
        color: chartColors.primary,
        opacity: 0.8
      },
      hovertemplate: '<b>%{x}</b><br>Properties: %{y}<extra></extra>'
    }]

    const layout = {
      ...defaultLayout,
      title: {
        text: 'Price Distribution',
        font: { size: 16, color: chartColors.text }
      },
      xaxis: {
        ...defaultLayout.xaxis,
        title: 'Price Range'
      },
      yaxis: {
        ...defaultLayout.yaxis,
        title: 'Number of Properties'
      }
    }

    return { data, layout }
  }, [stats, chartColors])

  // County Performance Chart
  const countyPerformanceChart = useMemo(() => {
    if (!stats?.top_counties) return null

    const data = [{
      x: stats.top_counties.map((c: any) => c.name),
      y: stats.top_counties.map((c: any) => c.avg_investment_score || 0),
      type: 'bar' as const,
      marker: {
        color: stats.top_counties.map((_: any, i: number) =>
          i === 0 ? chartColors.primary :
          i === 1 ? chartColors.secondary :
          i === 2 ? chartColors.accent : chartColors.grid
        ),
        opacity: 0.8
      },
      hovertemplate: '<b>%{x}</b><br>Avg Score: %{y:.1f}<extra></extra>'
    }]

    const layout = {
      ...defaultLayout,
      title: {
        text: 'County Investment Scores',
        font: { size: 16, color: chartColors.text }
      },
      xaxis: {
        ...defaultLayout.xaxis,
        title: 'County'
      },
      yaxis: {
        ...defaultLayout.yaxis,
        title: 'Average Investment Score'
      }
    }

    return { data, layout }
  }, [stats, chartColors])

  // Score Distribution Radar Chart
  const scoreDistributionChart = useMemo(() => {
    if (!stats?.score_distribution) return null

    const data = [{
      type: 'scatterpolar' as const,
      r: [
        stats.score_distribution.water_score || 0,
        stats.score_distribution.investment_score || 0,
        stats.score_distribution.county_market_score || 0,
        stats.score_distribution.geographic_score || 0,
        stats.score_distribution.description_score || 0,
        stats.score_distribution.water_score || 0 // Close the loop
      ],
      theta: [
        'Water Score',
        'Investment Score',
        'County Market',
        'Geographic',
        'Description',
        'Water Score'
      ],
      fill: 'toself' as const,
      fillcolor: `${chartColors.primary}20`,
      line: {
        color: chartColors.primary
      },
      hovertemplate: '<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>'
    }]

    const layout = {
      ...defaultLayout,
      title: {
        text: 'Average Score Distribution',
        font: { size: 16, color: chartColors.text }
      },
      polar: {
        radialaxis: {
          visible: true,
          range: [0, 100],
          color: chartColors.grid
        },
        angularaxis: {
          color: chartColors.text
        }
      }
    }

    return { data, layout }
  }, [stats, chartColors])

  // Activity Timeline Chart
  const activityTimelineChart = useMemo(() => {
    if (!stats?.activity_timeline) return null

    const data = [{
      x: stats.activity_timeline.dates,
      y: stats.activity_timeline.new_properties,
      type: 'scatter' as const,
      mode: 'lines+markers' as const,
      line: {
        color: chartColors.primary,
        width: 2
      },
      marker: {
        color: chartColors.primary,
        size: 6
      },
      name: 'New Properties',
      hovertemplate: '<b>%{x}</b><br>New Properties: %{y}<extra></extra>'
    }]

    const layout = {
      ...defaultLayout,
      title: {
        text: 'Property Addition Timeline',
        font: { size: 16, color: chartColors.text }
      },
      xaxis: {
        ...defaultLayout.xaxis,
        title: 'Date'
      },
      yaxis: {
        ...defaultLayout.yaxis,
        title: 'New Properties Added'
      }
    }

    return { data, layout }
  }, [stats, chartColors])

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Array(4).fill(0).map((_, i) => (
          <div key={i} className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
            <div className="animate-pulse">
              <div className="h-6 bg-surface rounded mb-4"></div>
              <div className="h-64 bg-surface rounded"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Price Distribution */}
      {priceDistributionChart && (
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <Plot
            data={priceDistributionChart.data}
            layout={priceDistributionChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        </div>
      )}

      {/* County Performance */}
      {countyPerformanceChart && (
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <Plot
            data={countyPerformanceChart.data}
            layout={countyPerformanceChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        </div>
      )}

      {/* Score Distribution Radar */}
      {scoreDistributionChart && (
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <Plot
            data={scoreDistributionChart.data}
            layout={scoreDistributionChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        </div>
      )}

      {/* Activity Timeline */}
      {activityTimelineChart && (
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <Plot
            data={activityTimelineChart.data}
            layout={activityTimelineChart.layout}
            config={defaultConfig}
            style={{ width: '100%', height: '300px' }}
          />
        </div>
      )}

      {/* If no chart data available */}
      {!priceDistributionChart && !countyPerformanceChart && !scoreDistributionChart && !activityTimelineChart && (
        <div className="col-span-2 bg-card rounded-lg p-8 border border-neutral-1 shadow-card text-center">
          <svg className="w-12 h-12 text-text-muted mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-medium text-text-primary mb-2">No Chart Data Available</h3>
          <p className="text-text-muted">Charts will appear here once data is loaded from the API.</p>
        </div>
      )}
    </div>
  )
}