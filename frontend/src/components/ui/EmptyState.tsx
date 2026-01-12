import React from 'react'
import { Search, Filter, Star, MapPin, TrendingUp, Database } from 'lucide-react'

type EmptyStateType = 'no-data' | 'no-results' | 'no-matches' | 'empty-watchlist' | 'empty-map' | 'no-activity'

interface EmptyStateProps {
  type?: EmptyStateType
  icon?: React.ReactNode
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  secondaryActionLabel?: string
  onSecondaryAction?: () => void
  className?: string
  compact?: boolean
}

interface EmptyStateConfig {
  icon: React.ReactNode
  title: string
  description: string
}

function getDefaultConfig(type: EmptyStateType): EmptyStateConfig {
  const configs: Record<EmptyStateType, EmptyStateConfig> = {
    'no-data': {
      icon: <Database className="w-12 h-12 text-text-muted" />,
      title: 'No data yet',
      description: 'Start by importing properties or running a scrape job to populate your database.'
    },
    'no-results': {
      icon: <Search className="w-12 h-12 text-text-muted" />,
      title: 'No results found',
      description: 'Try adjusting your search terms or filters to find what you\'re looking for.'
    },
    'no-matches': {
      icon: <Filter className="w-12 h-12 text-text-muted" />,
      title: 'No properties match your filters',
      description: 'Try broadening your filter criteria or resetting filters to see more results.'
    },
    'empty-watchlist': {
      icon: <Star className="w-12 h-12 text-text-muted" />,
      title: 'Your watchlist is empty',
      description: 'Star properties you\'re interested in to add them to your watchlist for easy tracking.'
    },
    'empty-map': {
      icon: <MapPin className="w-12 h-12 text-text-muted" />,
      title: 'No properties to display',
      description: 'Properties with location data will appear on the map. Try adjusting your filters.'
    },
    'no-activity': {
      icon: <TrendingUp className="w-12 h-12 text-text-muted" />,
      title: 'No recent activity',
      description: 'Activity will appear here as you review and triage properties.'
    }
  }

  return configs[type]
}

export function EmptyState({
  type = 'no-data',
  icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  className = '',
  compact = false
}: EmptyStateProps) {
  const defaultConfig = getDefaultConfig(type)

  const displayIcon = icon || defaultConfig.icon
  const displayTitle = title || defaultConfig.title
  const displayDescription = description || defaultConfig.description

  if (compact) {
    return (
      <div className={`flex items-center gap-3 py-6 px-4 text-center justify-center ${className}`}>
        <div className="text-text-muted">
          {React.cloneElement(displayIcon as React.ReactElement, {
            className: 'w-6 h-6'
          })}
        </div>
        <div>
          <p className="text-sm text-text-muted">{displayTitle}</p>
        </div>
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="text-sm text-accent-primary hover:underline font-medium"
          >
            {actionLabel}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}>
      <div className="mb-4 text-text-muted">
        {displayIcon}
      </div>
      <h3 className="text-lg font-semibold text-text-primary mb-2">
        {displayTitle}
      </h3>
      <p className="text-text-muted mb-6 max-w-md">
        {displayDescription}
      </p>
      <div className="flex gap-3">
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-colors"
          >
            {actionLabel}
          </button>
        )}
        {secondaryActionLabel && onSecondaryAction && (
          <button
            onClick={onSecondaryAction}
            className="px-4 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors"
          >
            {secondaryActionLabel}
          </button>
        )}
      </div>
    </div>
  )
}

interface TableEmptyStateProps {
  colSpan: number
  type?: EmptyStateType
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export function TableEmptyState({
  colSpan,
  type = 'no-results',
  title,
  description,
  actionLabel,
  onAction
}: TableEmptyStateProps) {
  return (
    <tr>
      <td colSpan={colSpan}>
        <EmptyState
          type={type}
          title={title}
          description={description}
          actionLabel={actionLabel}
          onAction={onAction}
        />
      </td>
    </tr>
  )
}

interface SearchEmptyStateProps {
  query: string
  onClear?: () => void
  className?: string
}

export function SearchEmptyState({ query, onClear, className = '' }: SearchEmptyStateProps) {
  return (
    <EmptyState
      type="no-results"
      title={`No results for "${query}"`}
      description="Try different keywords or check your spelling."
      actionLabel={onClear ? 'Clear search' : undefined}
      onAction={onClear}
      className={className}
      compact
    />
  )
}

interface FilterEmptyStateProps {
  activeFilterCount: number
  onResetFilters?: () => void
  className?: string
}

export function FilterEmptyState({
  activeFilterCount,
  onResetFilters,
  className = ''
}: FilterEmptyStateProps) {
  return (
    <EmptyState
      type="no-matches"
      title="No properties match your filters"
      description={`${activeFilterCount} filter${activeFilterCount !== 1 ? 's' : ''} applied. Try adjusting or removing some filters.`}
      actionLabel={onResetFilters ? 'Reset Filters' : undefined}
      onAction={onResetFilters}
      className={className}
    />
  )
}
