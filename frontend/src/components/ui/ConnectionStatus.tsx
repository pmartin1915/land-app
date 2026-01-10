import React, { useState, useEffect } from 'react'
import { Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { subscribeToConnectionStatus, getConnectionStatus, checkApiConnection } from '../../lib/api'

interface ConnectionStatusProps {
  className?: string
  showWhenOnline?: boolean
}

export function ConnectionStatus({ className = '', showWhenOnline = false }: ConnectionStatusProps) {
  const [isOnline, setIsOnline] = useState(getConnectionStatus())
  const [isRetrying, setIsRetrying] = useState(false)
  const [showBanner, setShowBanner] = useState(false)

  useEffect(() => {
    const unsubscribe = subscribeToConnectionStatus((online) => {
      setIsOnline(online)
      // Show banner when going offline, hide after 3 seconds when coming back online
      if (!online) {
        setShowBanner(true)
      } else {
        setTimeout(() => setShowBanner(false), 3000)
      }
    })

    return unsubscribe
  }, [])

  const handleRetry = async () => {
    setIsRetrying(true)
    try {
      const connected = await checkApiConnection()
      if (connected) {
        setIsOnline(true)
        setTimeout(() => setShowBanner(false), 1000)
      }
    } finally {
      setIsRetrying(false)
    }
  }

  // Don't show anything if online and showWhenOnline is false
  if (isOnline && !showWhenOnline && !showBanner) {
    return null
  }

  // Compact indicator for header/status bar
  if (!showBanner && showWhenOnline) {
    return (
      <div className={`flex items-center space-x-1 ${className}`}>
        {isOnline ? (
          <>
            <Wifi className="w-4 h-4 text-success" />
            <span className="text-xs text-success">Connected</span>
          </>
        ) : (
          <>
            <WifiOff className="w-4 h-4 text-error" />
            <span className="text-xs text-error">Offline</span>
          </>
        )}
      </div>
    )
  }

  // Full banner for offline state
  if (!isOnline || showBanner) {
    return (
      <div
        className={`
          fixed bottom-4 left-1/2 transform -translate-x-1/2 z-50
          px-4 py-3 rounded-lg shadow-lg
          flex items-center space-x-3
          transition-all duration-300
          ${isOnline
            ? 'bg-success/20 border border-success/30 text-success'
            : 'bg-error/20 border border-error/30 text-error'
          }
          ${className}
        `}
      >
        {isOnline ? (
          <>
            <Wifi className="w-5 h-5" />
            <span className="font-medium">Connection restored</span>
          </>
        ) : (
          <>
            <WifiOff className="w-5 h-5" />
            <div className="flex flex-col">
              <span className="font-medium">Connection lost</span>
              <span className="text-xs opacity-80">Retrying automatically...</span>
            </div>
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="ml-2 p-2 rounded-md hover:bg-white/10 transition-colors disabled:opacity-50"
              title="Retry connection"
            >
              <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
            </button>
          </>
        )}
      </div>
    )
  }

  return null
}

// Hook for components that need connection status
export function useConnectionStatus() {
  const [isOnline, setIsOnline] = useState(getConnectionStatus())

  useEffect(() => {
    const unsubscribe = subscribeToConnectionStatus(setIsOnline)
    return unsubscribe
  }, [])

  return isOnline
}
