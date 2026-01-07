import React from 'react'
import { AlertTriangle, WifiOff, ServerCrash, Clock, RefreshCw, HelpCircle } from 'lucide-react'

type ErrorType = 'network' | 'timeout' | 'server' | 'not-found' | 'unauthorized' | 'unknown'

interface ErrorStateProps {
  error: string | Error | null
  onRetry?: () => void
  className?: string
  compact?: boolean
  title?: string
}

function parseErrorType(error: string | Error | null): ErrorType {
  if (!error) return 'unknown'

  const errorMessage = typeof error === 'string' ? error : error.message
  const lowerMessage = errorMessage.toLowerCase()

  // Network errors
  if (
    lowerMessage.includes('network') ||
    lowerMessage.includes('fetch') ||
    lowerMessage.includes('failed to fetch') ||
    lowerMessage.includes('networkerror') ||
    lowerMessage.includes('cors')
  ) {
    return 'network'
  }

  // Timeout errors
  if (
    lowerMessage.includes('timeout') ||
    lowerMessage.includes('timed out') ||
    lowerMessage.includes('aborted')
  ) {
    return 'timeout'
  }

  // HTTP status codes
  if (lowerMessage.includes('401') || lowerMessage.includes('unauthorized')) {
    return 'unauthorized'
  }

  if (lowerMessage.includes('404') || lowerMessage.includes('not found')) {
    return 'not-found'
  }

  if (
    lowerMessage.includes('500') ||
    lowerMessage.includes('502') ||
    lowerMessage.includes('503') ||
    lowerMessage.includes('server error') ||
    lowerMessage.includes('internal error')
  ) {
    return 'server'
  }

  return 'unknown'
}

interface ErrorConfig {
  icon: React.ReactNode
  title: string
  message: string
  canRetry: boolean
  retryLabel: string
}

function getErrorConfig(type: ErrorType, customTitle?: string): ErrorConfig {
  const configs: Record<ErrorType, ErrorConfig> = {
    network: {
      icon: <WifiOff className="w-8 h-8 text-danger" />,
      title: customTitle || 'Connection Error',
      message: 'Unable to connect to the server. Please check your internet connection.',
      canRetry: true,
      retryLabel: 'Try Again'
    },
    timeout: {
      icon: <Clock className="w-8 h-8 text-warning" />,
      title: customTitle || 'Request Timeout',
      message: 'The request took too long to complete. The server may be busy.',
      canRetry: true,
      retryLabel: 'Retry'
    },
    server: {
      icon: <ServerCrash className="w-8 h-8 text-danger" />,
      title: customTitle || 'Server Error',
      message: 'Something went wrong on our end. Our team has been notified.',
      canRetry: true,
      retryLabel: 'Try Again'
    },
    'not-found': {
      icon: <HelpCircle className="w-8 h-8 text-text-muted" />,
      title: customTitle || 'Not Found',
      message: 'The requested resource could not be found.',
      canRetry: false,
      retryLabel: ''
    },
    unauthorized: {
      icon: <AlertTriangle className="w-8 h-8 text-warning" />,
      title: customTitle || 'Access Denied',
      message: 'You do not have permission to access this resource. Please check your API key.',
      canRetry: false,
      retryLabel: ''
    },
    unknown: {
      icon: <AlertTriangle className="w-8 h-8 text-danger" />,
      title: customTitle || 'Error',
      message: 'An unexpected error occurred. Please try again.',
      canRetry: true,
      retryLabel: 'Retry'
    }
  }

  return configs[type]
}

export function ErrorState({
  error,
  onRetry,
  className = '',
  compact = false,
  title
}: ErrorStateProps) {
  const errorType = parseErrorType(error)
  const config = getErrorConfig(errorType, title)
  const errorMessage = typeof error === 'string' ? error : error?.message

  if (compact) {
    return (
      <div className={`flex items-center gap-3 p-3 bg-danger/10 border border-danger/20 rounded-lg ${className}`}>
        <AlertTriangle className="w-5 h-5 text-danger flex-shrink-0" />
        <span className="text-danger text-sm flex-1">{config.message}</span>
        {config.canRetry && onRetry && (
          <button
            onClick={onRetry}
            className="px-3 py-1 bg-danger text-white text-sm rounded hover:bg-opacity-90 transition-colors flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            {config.retryLabel}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}>
      <div className="mb-4">
        {config.icon}
      </div>
      <h3 className="text-lg font-semibold text-text-primary mb-2">
        {config.title}
      </h3>
      <p className="text-text-muted mb-4 max-w-md">
        {config.message}
      </p>
      {errorMessage && errorType === 'unknown' && (
        <p className="text-xs text-text-muted mb-4 font-mono bg-surface p-2 rounded max-w-md overflow-hidden text-ellipsis">
          {errorMessage}
        </p>
      )}
      {config.canRetry && onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-opacity-90 transition-colors flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          {config.retryLabel}
        </button>
      )}
      {!config.canRetry && errorType === 'unauthorized' && (
        <a
          href="/settings"
          className="px-4 py-2 bg-surface text-text-primary border border-neutral-1 rounded-lg hover:bg-card transition-colors"
        >
          Go to Settings
        </a>
      )}
    </div>
  )
}

interface InlineErrorProps {
  error: string | Error | null
  onRetry?: () => void
  className?: string
}

export function InlineError({ error, onRetry, className = '' }: InlineErrorProps) {
  if (!error) return null

  const errorMessage = typeof error === 'string' ? error : error.message

  return (
    <div className={`flex items-center gap-2 text-danger text-sm ${className}`}>
      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
      <span>{errorMessage}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-danger hover:underline font-medium"
        >
          Retry
        </button>
      )}
    </div>
  )
}
