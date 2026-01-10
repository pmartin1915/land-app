import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { HelpCircle } from 'lucide-react'

export interface TooltipProps {
  /** Content to display in the tooltip */
  content: React.ReactNode
  /** Element to wrap (if not using help icon) */
  children?: React.ReactNode
  /** Show a help circle icon instead of wrapping children */
  showHelpIcon?: boolean
  /** Position of the tooltip relative to the trigger */
  position?: 'top' | 'bottom' | 'left' | 'right'
  /** Additional className for the tooltip container */
  className?: string
  /** Additional className for the help icon */
  iconClassName?: string
  /** Size of the help icon */
  iconSize?: number
}

/**
 * Reusable tooltip component with optional help icon.
 * Uses portal to render tooltip at document body level to avoid overflow clipping.
 */
export function Tooltip({
  content,
  children,
  showHelpIcon = false,
  position = 'top',
  className = '',
  iconClassName = '',
  iconSize = 14,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 })
  const [adjustedPosition, setAdjustedPosition] = useState(position)
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  // Calculate tooltip position when visible
  useEffect(() => {
    if (isVisible && triggerRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect()
      const tooltipWidth = 280 // max-width from CSS
      const tooltipHeight = 80 // approximate height
      const gap = 8 // spacing between trigger and tooltip

      let top = 0
      let left = 0
      let finalPosition = position

      // Calculate initial position
      switch (position) {
        case 'top':
          top = triggerRect.top - tooltipHeight - gap
          left = triggerRect.left + triggerRect.width / 2 - tooltipWidth / 2
          if (top < 0) {
            finalPosition = 'bottom'
            top = triggerRect.bottom + gap
          }
          break
        case 'bottom':
          top = triggerRect.bottom + gap
          left = triggerRect.left + triggerRect.width / 2 - tooltipWidth / 2
          if (top + tooltipHeight > window.innerHeight) {
            finalPosition = 'top'
            top = triggerRect.top - tooltipHeight - gap
          }
          break
        case 'left':
          top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2
          left = triggerRect.left - tooltipWidth - gap
          if (left < 0) {
            finalPosition = 'right'
            left = triggerRect.right + gap
          }
          break
        case 'right':
          top = triggerRect.top + triggerRect.height / 2 - tooltipHeight / 2
          left = triggerRect.right + gap
          if (left + tooltipWidth > window.innerWidth) {
            finalPosition = 'left'
            left = triggerRect.left - tooltipWidth - gap
          }
          break
      }

      // Clamp to viewport
      left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8))
      top = Math.max(8, top)

      setTooltipPosition({ top, left })
      setAdjustedPosition(finalPosition)
    }
  }, [isVisible, position])

  const trigger = showHelpIcon ? (
    <HelpCircle
      size={iconSize}
      className={`text-text-muted hover:text-text-primary cursor-help transition-colors ${iconClassName}`}
      aria-label="Help"
    />
  ) : (
    children
  )

  // Arrow styles based on position
  const getArrowStyles = () => {
    switch (adjustedPosition) {
      case 'top':
        return 'bottom-0 left-1/2 -translate-x-1/2 translate-y-full border-t-card border-x-transparent border-b-transparent'
      case 'bottom':
        return 'top-0 left-1/2 -translate-x-1/2 -translate-y-full border-b-card border-x-transparent border-t-transparent'
      case 'left':
        return 'right-0 top-1/2 -translate-y-1/2 translate-x-full border-l-card border-y-transparent border-r-transparent'
      case 'right':
        return 'left-0 top-1/2 -translate-y-1/2 -translate-x-full border-r-card border-y-transparent border-l-transparent'
      default:
        return ''
    }
  }

  return (
    <div
      ref={triggerRef}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {trigger}

      {isVisible && createPortal(
        <div
          ref={tooltipRef}
          role="tooltip"
          style={{
            position: 'fixed',
            top: tooltipPosition.top,
            left: tooltipPosition.left,
            zIndex: 9999,
          }}
          className="px-3 py-2 bg-card text-text-primary text-sm border border-neutral-1 rounded-lg shadow-elevated max-w-[280px] w-max animate-in fade-in-0 zoom-in-95 duration-150"
        >
          {content}
          {/* Arrow */}
          <div
            className={`absolute w-0 h-0 border-[6px] ${getArrowStyles()}`}
          />
        </div>,
        document.body
      )}
    </div>
  )
}

export default Tooltip
