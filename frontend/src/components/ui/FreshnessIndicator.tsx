import React, { useState, useEffect } from 'react'
import { Clock, RefreshCw } from 'lucide-react'

interface FreshnessIndicatorProps {
  timestamp: Date | string | null
  onRefresh?: () => void
  isRefreshing?: boolean
  showIcon?: boolean
  className?: string
}

function formatRelativeTime(timestamp: Date | string | null): string {
  if (!timestamp) return 'Never'

  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()

  // Handle future timestamps
  if (diffMs < 0) return 'Just now'

  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) return 'Just now'
  if (diffMinutes === 1) return '1 minute ago'
  if (diffMinutes < 60) return `${diffMinutes} minutes ago`
  if (diffHours === 1) return '1 hour ago'
  if (diffHours < 24) return `${diffHours} hours ago`
  if (diffDays === 1) return '1 day ago'
  if (diffDays < 7) return `${diffDays} days ago`

  // For older dates, show the actual date
  return date.toLocaleDateString()
}

function getFreshnessColor(timestamp: Date | string | null): string {
  if (!timestamp) return 'text-text-muted'

  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))

  // Fresh: less than 5 minutes
  if (diffMinutes < 5) return 'text-success'
  // Recent: less than 1 hour
  if (diffMinutes < 60) return 'text-accent-primary'
  // Stale: less than 24 hours
  if (diffMinutes < 60 * 24) return 'text-warning'
  // Very stale: more than 24 hours
  return 'text-danger'
}

export function FreshnessIndicator({
  timestamp,
  onRefresh,
  isRefreshing = false,
  showIcon = true,
  className = ''
}: FreshnessIndicatorProps) {
  const [, setTick] = useState(0)

  // Update every minute to keep the relative time fresh
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1)
    }, 60 * 1000)

    return () => clearInterval(interval)
  }, [])

  const relativeTime = formatRelativeTime(timestamp)
  const colorClass = getFreshnessColor(timestamp)

  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      {showIcon && <Clock className={`w-3.5 h-3.5 ${colorClass}`} />}
      <span className={`text-xs ${colorClass}`}>
        Updated {relativeTime}
      </span>
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className={`p-0.5 rounded hover:bg-surface transition-colors ${colorClass} disabled:opacity-50`}
          title="Refresh data"
          aria-label="Refresh data"
        >
          <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      )}
    </div>
  )
}

interface FreshnessBadgeProps {
  timestamp: Date | string | null
  className?: string
}

export function FreshnessBadge({ timestamp, className = '' }: FreshnessBadgeProps) {
  const [, setTick] = useState(0)

  // Update every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1)
    }, 60 * 1000)

    return () => clearInterval(interval)
  }, [])

  if (!timestamp) return null

  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))

  // Only show badge for stale data (more than 1 hour old)
  if (diffMinutes < 60) return null

  const bgColor = diffMinutes < 60 * 24 ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bgColor} ${className}`}>
      <Clock className="w-3 h-3" />
      {diffMinutes < 60 * 24 ? 'Stale data' : 'Old data'}
    </span>
  )
}

interface DataTimestampProps {
  label?: string
  timestamp: Date | string | null
  onRefresh?: () => void
  isRefreshing?: boolean
  className?: string
}

export function DataTimestamp({
  label = 'Last updated',
  timestamp,
  onRefresh,
  isRefreshing = false,
  className = ''
}: DataTimestampProps) {
  const [, setTick] = useState(0)

  // Update every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1)
    }, 60 * 1000)

    return () => clearInterval(interval)
  }, [])

  const relativeTime = formatRelativeTime(timestamp)
  const colorClass = getFreshnessColor(timestamp)

  return (
    <div className={`flex items-center gap-2 text-xs ${className}`}>
      <span className="text-text-muted">{label}:</span>
      <span className={colorClass}>{relativeTime}</span>
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-1 rounded hover:bg-surface transition-colors text-text-muted hover:text-text-primary disabled:opacity-50"
          title="Refresh"
          aria-label="Refresh data"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      )}
    </div>
  )
}
