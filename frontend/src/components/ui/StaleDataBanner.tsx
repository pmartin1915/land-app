import React from 'react'
import { Clock, RefreshCw, WifiOff } from 'lucide-react'

interface StaleDataBannerProps {
  lastFetchTime: Date | null
  onRefresh?: () => void
  isRefreshing?: boolean
  className?: string
  compact?: boolean
}

/**
 * Banner component to indicate that displayed data is from cache
 * and may be outdated due to connection issues.
 */
export function StaleDataBanner({
  lastFetchTime,
  onRefresh,
  isRefreshing = false,
  className = '',
  compact = false
}: StaleDataBannerProps) {
  const formatTimeAgo = (date: Date | null): string => {
    if (!date) return 'unknown time'

    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
    return date.toLocaleDateString()
  }

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2 py-1 bg-warning/10 text-warning text-xs rounded ${className}`}>
        <WifiOff className="w-3 h-3" />
        <span>Cached</span>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="ml-1 hover:text-warning/80 disabled:opacity-50"
            aria-label="Refresh data"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 bg-warning/10 border border-warning/20 rounded-lg ${className}`}>
      <Clock className="w-4 h-4 text-warning flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-warning text-sm">
          Showing cached data
          {lastFetchTime && (
            <span className="text-warning/70"> from {formatTimeAgo(lastFetchTime)}</span>
          )}
        </span>
        <p className="text-warning/60 text-xs mt-0.5">
          Unable to connect to server. Data may be outdated.
        </p>
      </div>
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-warning/20 text-warning text-sm rounded hover:bg-warning/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Refresh data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Retrying...' : 'Retry'}
        </button>
      )}
    </div>
  )
}
