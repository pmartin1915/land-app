import React, { useState } from 'react'
import { useComponentTheme } from '../lib/theme-provider'
import { usePropertyStats, useTriageQueue, useCounties, useWorkflowStats } from '../lib/hooks'
import { PropertyFilters } from '../types'
import { DashboardCharts } from '../components/DashboardCharts'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendText?: string
  className?: string
  isLoading?: boolean
}

function KPICard({ title, value, subtitle, icon, trend, trendText, className = '', isLoading }: KPICardProps) {
  const trendColors = {
    up: 'text-success',
    down: 'text-danger',
    neutral: 'text-text-muted'
  }

  if (isLoading) {
    return (
      <div className={`bg-card rounded-lg p-6 border border-neutral-1 shadow-card hover:shadow-elevated transition-shadow duration-200 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-surface rounded mb-2"></div>
          <div className="h-8 bg-surface rounded mb-2"></div>
          <div className="h-3 bg-surface rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-card rounded-lg p-6 border border-neutral-1 shadow-card hover:shadow-elevated transition-shadow duration-200 ${className}`}>
      <h3 className="text-sm font-medium text-text-muted mb-2">{title}</h3>
      <p className="text-2xl font-bold text-text-primary">{value}</p>
      {(subtitle || trendText) && (
        <div className={`mt-2 flex items-center text-xs ${trend ? trendColors[trend] : 'text-text-muted'}`}>
          {icon}
          <span>{subtitle || trendText}</span>
        </div>
      )}
    </div>
  )
}

export function Dashboard() {
  const theme = useComponentTheme()
  const [filters] = useState<PropertyFilters>({})

  // Fetch data using hooks
  const { data: stats, loading: statsLoading, error: statsError } = usePropertyStats(filters)
  const { data: triageQueue, loading: triageLoading } = useTriageQueue()
  const { data: counties, loading: countiesLoading } = useCounties()
  const { data: workflowStats, loading: workflowLoading } = useWorkflowStats()

  // Calculate derived metrics
  const upcomingAuctions = stats?.upcoming_auctions || 0
  const newItems = stats?.new_items_7d || 0
  const needsReview = triageQueue?.length || 0
  const watchlistCount = stats?.watchlist_count || 0
  const totalProperties = stats?.total_properties || 0
  const avgInvestmentScore = stats?.avg_investment_score || 0

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Dashboard</h1>
        <p className="text-text-muted">High-level health and quick triage</p>
      </div>

      {/* Error State */}
      {statsError && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-lg">
          <p className="text-danger text-sm">Error loading dashboard data: {statsError}</p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Total Properties"
          value={totalProperties.toLocaleString()}
          icon={
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z" />
              <path fillRule="evenodd" d="M3 8a2 2 0 012-2v9a2 2 0 102 0V6a2 2 0 012-2h6a2 2 0 012 2v9a2 2 0 102 0V6a2 2 0 012 2 2 2 0 11-4 0V6a2 2 0 00-2-2V4a2 2 0 00-2-2H5a2 2 0 00-2 2v2a2 2 0 00-2 2z" clipRule="evenodd" />
            </svg>
          }
          subtitle="In database"
          isLoading={statsLoading}
        />

        <KPICard
          title="New Items (7d)"
          value={newItems.toLocaleString()}
          icon={
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
          }
          trend="up"
          trendText={stats?.new_items_trend || "Recently added"}
          isLoading={statsLoading}
        />

        <KPICard
          title="Needs Review"
          value={needsReview.toLocaleString()}
          icon={
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          }
          subtitle="AI suggestions pending"
          className={needsReview > 0 ? 'border-warning' : ''}
          isLoading={triageLoading}
        />

        <KPICard
          title="Avg Investment Score"
          value={avgInvestmentScore ? avgInvestmentScore.toFixed(1) : 'N/A'}
          icon={
            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          }
          subtitle="Portfolio quality"
          isLoading={statsLoading}
        />
      </div>

      {/* Secondary Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-card rounded-lg p-4 border border-neutral-1 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Counties Active</p>
              <p className="text-lg font-semibold text-text-primary">
                {countiesLoading ? '...' : counties?.length || 0}
              </p>
            </div>
            <div className="w-8 h-8 bg-accent-primary/10 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-accent-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-card rounded-lg p-4 border border-neutral-1 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Water Access</p>
              <p className="text-lg font-semibold text-text-primary">
                {statsLoading ? '...' : `${stats?.water_access_percentage || 0}%`}
              </p>
            </div>
            <div className="w-8 h-8 bg-accent-secondary/10 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-accent-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-card rounded-lg p-4 border border-neutral-1 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-muted">Avg Price/Acre</p>
              <p className="text-lg font-semibold text-text-primary">
                {statsLoading ? '...' : `$${stats?.avg_price_per_acre?.toLocaleString() || 0}`}
              </p>
            </div>
            <div className="w-8 h-8 bg-success/10 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Research Pipeline */}
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Research Pipeline</h2>
            <p className="text-sm text-text-muted">Property workflow status breakdown</p>
          </div>
          {workflowStats && (
            <span className="text-sm text-text-muted">
              {workflowStats.total.toLocaleString()} total properties
            </span>
          )}
        </div>

        {workflowLoading ? (
          <div className="animate-pulse">
            <div className="h-8 bg-surface rounded mb-4"></div>
            <div className="grid grid-cols-5 gap-4">
              {Array(5).fill(0).map((_, i) => (
                <div key={i} className="h-20 bg-surface rounded"></div>
              ))}
            </div>
          </div>
        ) : workflowStats ? (
          <>
            {/* Progress bar */}
            <div className="h-4 bg-surface rounded-full overflow-hidden mb-6 flex">
              {workflowStats.new > 0 && (
                <div
                  className="bg-neutral-2 transition-all duration-300"
                  style={{ width: `${(workflowStats.new / workflowStats.total) * 100}%` }}
                  title={`New: ${workflowStats.new}`}
                />
              )}
              {workflowStats.reviewing > 0 && (
                <div
                  className="bg-warning transition-all duration-300"
                  style={{ width: `${(workflowStats.reviewing / workflowStats.total) * 100}%` }}
                  title={`Reviewing: ${workflowStats.reviewing}`}
                />
              )}
              {workflowStats.bid_ready > 0 && (
                <div
                  className="bg-success transition-all duration-300"
                  style={{ width: `${(workflowStats.bid_ready / workflowStats.total) * 100}%` }}
                  title={`Bid Ready: ${workflowStats.bid_ready}`}
                />
              )}
              {workflowStats.rejected > 0 && (
                <div
                  className="bg-danger transition-all duration-300"
                  style={{ width: `${(workflowStats.rejected / workflowStats.total) * 100}%` }}
                  title={`Rejected: ${workflowStats.rejected}`}
                />
              )}
              {workflowStats.purchased > 0 && (
                <div
                  className="bg-accent-primary transition-all duration-300"
                  style={{ width: `${(workflowStats.purchased / workflowStats.total) * 100}%` }}
                  title={`Purchased: ${workflowStats.purchased}`}
                />
              )}
            </div>

            {/* Status cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-4 bg-surface rounded-lg border border-neutral-1">
                <div className="w-3 h-3 bg-neutral-2 rounded-full mx-auto mb-2"></div>
                <p className="text-2xl font-bold text-text-primary">{workflowStats.new.toLocaleString()}</p>
                <p className="text-sm text-text-muted">New</p>
              </div>
              <div className="text-center p-4 bg-surface rounded-lg border border-warning/30">
                <div className="w-3 h-3 bg-warning rounded-full mx-auto mb-2"></div>
                <p className="text-2xl font-bold text-text-primary">{workflowStats.reviewing.toLocaleString()}</p>
                <p className="text-sm text-text-muted">Reviewing</p>
              </div>
              <div className="text-center p-4 bg-surface rounded-lg border border-success/30">
                <div className="w-3 h-3 bg-success rounded-full mx-auto mb-2"></div>
                <p className="text-2xl font-bold text-text-primary">{workflowStats.bid_ready.toLocaleString()}</p>
                <p className="text-sm text-text-muted">Bid Ready</p>
              </div>
              <div className="text-center p-4 bg-surface rounded-lg border border-danger/30">
                <div className="w-3 h-3 bg-danger rounded-full mx-auto mb-2"></div>
                <p className="text-2xl font-bold text-text-primary">{workflowStats.rejected.toLocaleString()}</p>
                <p className="text-sm text-text-muted">Rejected</p>
              </div>
              <div className="text-center p-4 bg-surface rounded-lg border border-accent-primary/30">
                <div className="w-3 h-3 bg-accent-primary rounded-full mx-auto mb-2"></div>
                <p className="text-2xl font-bold text-text-primary">{workflowStats.purchased.toLocaleString()}</p>
                <p className="text-sm text-text-muted">Purchased</p>
              </div>
            </div>
          </>
        ) : (
          <p className="text-text-muted text-center py-4">Unable to load workflow statistics</p>
        )}
      </div>

      {/* Interactive Charts Section */}
      <div className="mb-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-text-primary mb-2">Analytics & Insights</h2>
          <p className="text-text-muted">Visual analysis of property data and trends</p>
        </div>
        <DashboardCharts stats={stats} isLoading={statsLoading} />
      </div>

      {/* Timeline and Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Counties by Properties */}
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Top Counties by Properties</h2>
          <div className="space-y-3">
            {statsLoading ? (
              Array(3).fill(0).map((_, i) => (
                <div key={i} className="animate-pulse flex items-center justify-between p-3 bg-surface rounded border border-neutral-1">
                  <div>
                    <div className="h-4 bg-neutral-1 rounded w-24 mb-1"></div>
                    <div className="h-3 bg-neutral-1 rounded w-16"></div>
                  </div>
                  <div className="h-6 bg-neutral-1 rounded w-12"></div>
                </div>
              ))
            ) : (
              stats?.top_counties?.map((county, index) => (
                <div key={county.name} className="flex items-center justify-between p-3 bg-surface rounded border border-neutral-1 hover:bg-card transition-colors">
                  <div>
                    <p className="font-medium text-text-primary">{county.name}</p>
                    <p className="text-sm text-text-muted">{county.properties} properties</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-accent-primary">#{index + 1}</p>
                    <p className="text-xs text-text-muted">${county.avg_price?.toLocaleString() || 0}</p>
                  </div>
                </div>
              )) || (
                <p className="text-text-muted text-center py-4">No county data available</p>
              )
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {stats?.recent_activity?.map((activity, index) => (
              <div key={index} className="flex items-center space-x-3 p-2 rounded hover:bg-surface transition-colors duration-150">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  activity.type === 'success' ? 'bg-success' :
                  activity.type === 'warning' ? 'bg-warning' :
                  activity.type === 'info' ? 'bg-accent-primary' : 'bg-accent-alt'
                }`}></div>
                <span className="text-text-muted flex-1">{activity.message}</span>
                <span className="text-xs text-text-muted">{activity.time}</span>
              </div>
            )) || (
              statsLoading ? (
                Array(4).fill(0).map((_, i) => (
                  <div key={i} className="animate-pulse flex items-center space-x-3 p-2">
                    <div className="w-2 h-2 bg-neutral-1 rounded-full"></div>
                    <div className="flex-1 h-4 bg-neutral-1 rounded"></div>
                    <div className="w-16 h-3 bg-neutral-1 rounded"></div>
                  </div>
                ))
              ) : (
                <p className="text-text-muted text-center py-4">No recent activity</p>
              )
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-card rounded-lg p-6 border border-neutral-1 shadow-card">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button
            className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-all duration-150 flex items-center space-x-2"
            disabled={triageLoading}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <span>{triageLoading ? 'Loading...' : `Start Triage ${needsReview > 0 ? `(${needsReview})` : ''}`}</span>
          </button>

          <button className="px-4 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-all duration-150 flex items-center space-x-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
            </svg>
            <span>Import CSV</span>
          </button>

          <button className="px-4 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-all duration-150 flex items-center space-x-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>View Reports</span>
          </button>
        </div>
      </div>
    </div>
  )
}