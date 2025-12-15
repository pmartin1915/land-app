import React, { ReactNode, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { ThemeToggle, useComponentTheme } from '../lib/theme-provider'
import { LeftRail } from './LeftRail'
import { TopBar } from './TopBar'
import { PropertyFilters } from '../types'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const theme = useComponentTheme()
  const [globalFilters, setGlobalFilters] = useState<PropertyFilters>({})
  const [globalSearchQuery, setGlobalSearchQuery] = useState('')

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
      '/reports': 'Reports / Exports',
      '/settings': 'Settings',
    }
    return routes[pathname] || 'Alabama Auction Watcher'
  }

  const handleFiltersChange = (filters: PropertyFilters) => {
    setGlobalFilters(filters)
    // TODO: Pass filters to child components via context or props
  }

  const handleSearchChange = (query: string, results: any[]) => {
    setGlobalSearchQuery(query)
    // TODO: Pass search results to child components via context or props
  }

  return (
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
    </div>
  )
}