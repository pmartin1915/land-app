import React, { ReactNode, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { LeftRail } from './LeftRail'
import { TopBar } from './TopBar'
import { ConnectionStatus } from './ui/ConnectionStatus'
import { PropertyFilters } from '../types'
import { PropertyCompareProvider } from './PropertyCompareContext'
import { PropertyCompareModal } from './PropertyCompareModal'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [, setGlobalFilters] = useState<PropertyFilters>({})
  const [, setGlobalSearchQuery] = useState('')

  // Get page title based on current route
  const getPageTitle = (pathname: string): string => {
    const routes: { [key: string]: string } = {
      '/': 'Dashboard',
      '/dashboard': 'Dashboard',
      '/parcels': 'Parcels',
      '/map': 'Map',
      '/triage': 'Triage / AI Suggestions',
      '/scrape-jobs': 'Scrape Jobs',
      '/watchlist': 'Watchlist',
      '/my-first-deal': 'My First Deal',
      '/reports': 'Reports / Exports',
      '/settings': 'Settings',
    }
    return routes[pathname] || 'Auction Watcher'
  }

  const handleFiltersChange = (filters: PropertyFilters) => {
    setGlobalFilters(filters)
    // TODO: Pass filters to child components via context or props
  }

  const handleSearchChange = (query: string, _results: unknown[]) => {
    setGlobalSearchQuery(query)
    // TODO: Pass search results to child components via context or props
  }

  return (
    <PropertyCompareProvider>
      <div className="layout flex h-screen overflow-hidden">
        {/* Left Rail Navigation */}
        <LeftRail />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Enhanced Top Bar */}
          <TopBar
            title={getPageTitle(location.pathname)}
            onFiltersChange={handleFiltersChange}
            onSearchChange={handleSearchChange}
          />

          {/* Main Canvas */}
          <div className="flex-1 overflow-hidden bg-bg">
            {children}
          </div>
        </div>

        {/* Connection Status Banner */}
        <ConnectionStatus />

        {/* Property Comparison Modal */}
        <PropertyCompareModal />
      </div>
    </PropertyCompareProvider>
  )
}