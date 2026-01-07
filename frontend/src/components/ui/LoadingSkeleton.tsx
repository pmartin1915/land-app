import React from 'react'

type SkeletonVariant = 'text' | 'card' | 'row' | 'circular' | 'rectangular'

interface LoadingSkeletonProps {
  variant?: SkeletonVariant
  width?: string | number
  height?: string | number
  count?: number
  className?: string
}

export function LoadingSkeleton({
  variant = 'text',
  width,
  height,
  count = 1,
  className = ''
}: LoadingSkeletonProps) {
  const baseClasses = 'animate-pulse bg-surface rounded'

  const variantClasses: Record<SkeletonVariant, string> = {
    text: 'h-4 rounded',
    card: 'h-24 rounded-lg',
    row: 'h-12 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg'
  }

  const getStyle = (): React.CSSProperties => {
    const style: React.CSSProperties = {}

    if (width) {
      style.width = typeof width === 'number' ? `${width}px` : width
    }
    if (height) {
      style.height = typeof height === 'number' ? `${height}px` : height
    }

    // Default dimensions for circular
    if (variant === 'circular' && !width && !height) {
      style.width = '40px'
      style.height = '40px'
    }

    return style
  }

  const skeletons = Array(count).fill(0).map((_, i) => (
    <div
      key={i}
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={getStyle()}
    />
  ))

  if (count === 1) {
    return skeletons[0]
  }

  return <div className="space-y-2">{skeletons}</div>
}

interface TableSkeletonProps {
  rows?: number
  columns?: number
  showHeader?: boolean
  className?: string
}

export function TableSkeleton({
  rows = 10,
  columns = 8,
  showHeader = true,
  className = ''
}: TableSkeletonProps) {
  return (
    <div className={`w-full ${className}`}>
      {showHeader && (
        <div className="flex gap-4 px-4 py-3 border-b border-neutral-1 bg-surface">
          {Array(columns).fill(0).map((_, i) => (
            <div
              key={`header-${i}`}
              className="animate-pulse bg-neutral-1 rounded h-4"
              style={{ width: i === 0 ? '24px' : `${60 + Math.random() * 40}px` }}
            />
          ))}
        </div>
      )}
      {Array(rows).fill(0).map((_, rowIndex) => (
        <div
          key={`row-${rowIndex}`}
          className="flex gap-4 px-4 py-3 border-b border-neutral-1"
        >
          {Array(columns).fill(0).map((_, colIndex) => (
            <div
              key={`cell-${rowIndex}-${colIndex}`}
              className="animate-pulse bg-surface rounded h-4"
              style={{ width: colIndex === 0 ? '24px' : `${60 + Math.random() * 60}px` }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

interface CardSkeletonProps {
  showIcon?: boolean
  showSubtitle?: boolean
  className?: string
}

export function CardSkeleton({
  showIcon = true,
  showSubtitle = true,
  className = ''
}: CardSkeletonProps) {
  return (
    <div className={`bg-card rounded-lg p-6 border border-neutral-1 shadow-card ${className}`}>
      <div className="animate-pulse">
        {showIcon && (
          <div className="flex justify-between items-start mb-4">
            <div className="h-4 bg-surface rounded w-24" />
            <div className="h-8 w-8 bg-surface rounded-full" />
          </div>
        )}
        <div className="h-8 bg-surface rounded w-20 mb-2" />
        {showSubtitle && <div className="h-3 bg-surface rounded w-16" />}
      </div>
    </div>
  )
}

interface KPICardSkeletonProps {
  count?: number
  className?: string
}

export function KPICardsSkeleton({ count = 4, className = '' }: KPICardSkeletonProps) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${className}`}>
      {Array(count).fill(0).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}

interface ListSkeletonProps {
  items?: number
  showAvatar?: boolean
  className?: string
}

export function ListSkeleton({
  items = 5,
  showAvatar = false,
  className = ''
}: ListSkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array(items).fill(0).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 bg-surface rounded border border-neutral-1">
          {showAvatar && (
            <div className="animate-pulse w-10 h-10 bg-neutral-1 rounded-full flex-shrink-0" />
          )}
          <div className="flex-1 space-y-2">
            <div className="animate-pulse h-4 bg-neutral-1 rounded w-3/4" />
            <div className="animate-pulse h-3 bg-neutral-1 rounded w-1/2" />
          </div>
          <div className="animate-pulse h-6 w-12 bg-neutral-1 rounded" />
        </div>
      ))}
    </div>
  )
}
