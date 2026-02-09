import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

interface Props {
  children: ReactNode
  routeName?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Route-specific Error Boundary that catches errors within a single route
 * and allows navigation to other routes without crashing the entire app.
 */
export class RouteErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error(`[RouteErrorBoundary${this.props.routeName ? `:${this.props.routeName}` : ''}] Error:`, error)
    console.error('[RouteErrorBoundary] Component stack:', errorInfo.componentStack)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null })
  }

  handleGoHome = (): void => {
    // Reset error state and navigate to home
    this.setState({ hasError: false, error: null })
    window.location.href = '/'
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] p-8">
          <div className="bg-surface border border-border rounded-lg p-8 max-w-md w-full text-center">
            <AlertTriangle className="w-12 h-12 text-warning mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              Page Error
            </h2>
            <p className="text-text-secondary mb-4">
              Something went wrong loading this page. You can try again or return to the dashboard.
            </p>
            {this.state.error && (
              <details className="text-left mb-4 p-3 bg-bg rounded border border-border">
                <summary className="text-sm text-text-muted cursor-pointer">
                  Technical details
                </summary>
                <pre className="text-xs text-error mt-2 overflow-auto max-h-32">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              <button
                onClick={this.handleGoHome}
                className="flex items-center gap-2 px-4 py-2 bg-surface border border-border rounded-md hover:bg-hover transition-colors"
              >
                <Home className="w-4 h-4" />
                Dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
