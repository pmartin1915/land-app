import { useEffect, useRef, useCallback } from 'react'

/**
 * Focusable element selectors for accessibility.
 * Includes all common interactive elements.
 */
const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * Custom hook that traps focus within a container element.
 * Essential for modal accessibility - prevents users from tabbing outside the modal.
 *
 * @param isActive - Whether the focus trap is currently active
 * @returns A ref to attach to the container element
 *
 * @example
 * ```tsx
 * function Modal({ isOpen, onClose }) {
 *   const focusTrapRef = useFocusTrap(isOpen)
 *
 *   return (
 *     <div ref={focusTrapRef} role="dialog" aria-modal="true">
 *       <button onClick={onClose}>Close</button>
 *       <p>Modal content</p>
 *     </div>
 *   )
 * }
 * ```
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(isActive: boolean) {
  const containerRef = useRef<T>(null)
  const previousActiveElementRef = useRef<HTMLElement | null>(null)

  /**
   * Get all focusable elements within the container
   */
  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return []

    const elements = containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
    return Array.from(elements).filter(el => {
      // Filter out hidden elements
      return el.offsetParent !== null && !el.hasAttribute('hidden')
    })
  }, [])

  /**
   * Handle Tab key to trap focus within the container
   */
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key !== 'Tab') return

    const focusableElements = getFocusableElements()
    if (focusableElements.length === 0) return

    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    // Shift+Tab on first element -> go to last
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault()
      lastElement.focus()
    }
    // Tab on last element -> go to first
    else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault()
      firstElement.focus()
    }
  }, [getFocusableElements])

  useEffect(() => {
    if (!isActive) return

    // Store the currently focused element to restore later
    previousActiveElementRef.current = document.activeElement as HTMLElement

    // Focus the first focusable element in the container
    const focusableElements = getFocusableElements()
    if (focusableElements.length > 0) {
      // Small delay to ensure the modal is rendered
      requestAnimationFrame(() => {
        focusableElements[0].focus()
      })
    }

    // Add keyboard event listener
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)

      // Restore focus to the previously focused element
      if (previousActiveElementRef.current && previousActiveElementRef.current.focus) {
        previousActiveElementRef.current.focus()
      }
    }
  }, [isActive, getFocusableElements, handleKeyDown])

  return containerRef
}

export default useFocusTrap
