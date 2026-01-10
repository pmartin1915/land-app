import React, { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useComponentTheme } from '../lib/theme-provider'
import { useApp } from '../lib/context'
import { NavigationItem } from '../types'

// Navigation items configuration based on design specification
const navigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: 'home',
    route: '/dashboard',
    shortcut: 'Cmd+1',
  },
  {
    id: 'parcels',
    label: 'Parcels',
    icon: 'database',
    route: '/parcels',
    shortcut: 'Cmd+2',
  },
  {
    id: 'map',
    label: 'Map',
    icon: 'map',
    route: '/map',
    shortcut: 'Cmd+3',
  },
  {
    id: 'triage',
    label: 'Triage / AI Suggestions',
    icon: 'alert-triangle',
    route: '/triage',
    shortcut: 'Cmd+T',
    badge: 15, // TODO: Connect to actual triage count
  },
  {
    id: 'scrape-jobs',
    label: 'Scrape Jobs',
    icon: 'refresh-cw',
    route: '/scrape-jobs',
  },
  {
    id: 'watchlist',
    label: 'Watchlist',
    icon: 'star',
    route: '/watchlist',
    badge: 8, // TODO: Connect to actual watchlist count
  },
  {
    id: 'my-first-deal',
    label: 'My First Deal',
    icon: 'sparkles',
    route: '/my-first-deal',
  },
  {
    id: 'reports',
    label: 'Reports / Exports',
    icon: 'file-text',
    route: '/reports',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'settings',
    route: '/settings',
  },
]

// Icon component mapping
const IconMap: { [key: string]: React.FC<{ className?: string }> } = {
  home: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  database: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
    </svg>
  ),
  map: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
    </svg>
  ),
  'alert-triangle': ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.864-.833-2.634 0L4.28 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  ),
  'refresh-cw': ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  star: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
    </svg>
  ),
  sparkles: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
    </svg>
  ),
  'file-text': ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  settings: ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  'chevron-left': ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  ),
  'chevron-right': ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
}

interface LeftRailProps {
  className?: string
}

export function LeftRail({ className = '' }: LeftRailProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const theme = useComponentTheme()
  const { state, dispatch } = useApp()

  const [collapsed, setCollapsed] = useState(false)
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  const handleNavigate = (item: NavigationItem) => {
    navigate(item.route)
    dispatch({ type: 'SET_LOADING', payload: true })
  }

  const toggleCollapsed = () => {
    setCollapsed(!collapsed)
  }

  const isActive = (route: string) => {
    if (route === '/dashboard' && location.pathname === '/') return true
    return location.pathname === route
  }

  // Get icons for toggle buttons
  const ChevronLeft = IconMap['chevron-left']
  const ChevronRight = IconMap['chevron-right']

  return (
    <div
      className={`
        ${collapsed ? 'w-16' : 'w-64'}
        bg-surface border-r border-neutral-1 flex-shrink-0
        transition-all duration-200 ease-out
        flex flex-col h-full
        ${className}
      `}
    >
      {/* Header */}
      <div className="p-4 border-b border-neutral-1">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-accent-primary rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold text-sm">AAW</span>
              </div>
              <div>
                <h2 className="text-sm font-semibold text-text-primary leading-tight">
                  Alabama Auction Watcher
                </h2>
                <p className="text-xs text-text-muted">Desktop v1.0</p>
              </div>
            </div>
          )}

          {collapsed && (
            <div className="w-8 h-8 bg-accent-primary rounded-lg flex items-center justify-center mx-auto">
              <span className="text-white font-bold text-sm">AAW</span>
            </div>
          )}

          <button
            onClick={toggleCollapsed}
            className="p-1 rounded hover:bg-card transition-colors duration-150 text-text-muted hover:text-text-primary"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 p-4 space-y-2">
        {navigationItems.map((item) => {
          const Icon = IconMap[item.icon]
          const active = isActive(item.route)

          return (
            <div
              key={item.id}
              className="relative"
              onMouseEnter={() => setHoveredItem(item.id)}
              onMouseLeave={() => setHoveredItem(null)}
            >
              <button
                onClick={() => handleNavigate(item)}
                className={`
                  w-full flex items-center space-x-3 px-3 py-2 rounded-lg
                  transition-all duration-150 ease-out group
                  ${active
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'text-text-muted hover:text-text-primary hover:bg-card'
                  }
                  ${collapsed ? 'justify-center' : 'justify-start'}
                `}
                title={collapsed ? item.label : undefined}
              >
                <div className="relative flex-shrink-0">
                  <Icon className="w-5 h-5" />
                  {item.badge && (
                    <span className={`
                      absolute -top-1 -right-1
                      w-4 h-4 text-xs font-medium
                      rounded-full flex items-center justify-center
                      ${active
                        ? 'bg-white text-accent-primary'
                        : 'bg-danger text-white'
                      }
                    `}>
                      {item.badge > 99 ? '99+' : item.badge}
                    </span>
                  )}
                </div>

                {!collapsed && (
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium">{item.label}</div>
                    {item.shortcut && (
                      <div className="text-xs opacity-60">{item.shortcut}</div>
                    )}
                  </div>
                )}
              </button>

              {/* Tooltip for collapsed state */}
              {collapsed && hoveredItem === item.id && (
                <div className={`
                  absolute left-full ml-2 top-0 z-50
                  bg-card border border-neutral-1 rounded-lg px-3 py-2 shadow-elevated
                  text-sm text-text-primary whitespace-nowrap
                  opacity-0 animate-in fade-in-0 zoom-in-95 duration-150
                `}>
                  <div className="font-medium">{item.label}</div>
                  {item.shortcut && (
                    <div className="text-xs text-text-muted">{item.shortcut}</div>
                  )}
                  {item.badge && (
                    <div className="text-xs text-danger">{item.badge} items</div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-neutral-1">
        {!collapsed && (
          <div className="space-y-2">
            <button className="w-full px-3 py-2 text-sm text-text-muted hover:text-text-primary hover:bg-card rounded-lg transition-colors duration-150 text-left">
              Quick Help
            </button>
            <button className="w-full px-3 py-2 text-sm text-text-muted hover:text-text-primary hover:bg-card rounded-lg transition-colors duration-150 text-left">
              Keyboard Shortcuts
            </button>
            <div className="pt-2 border-t border-neutral-1">
              <div className="text-xs text-text-muted">
                <div>Backend: {state.loading ? 'Connecting...' : 'Connected'}</div>
                <div>Last sync: 2 min ago</div>
              </div>
            </div>
          </div>
        )}

        {collapsed && (
          <div className="flex flex-col space-y-2 items-center">
            <button
              className="p-2 text-text-muted hover:text-text-primary hover:bg-card rounded-lg transition-colors duration-150"
              title="Help"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <div className={`w-2 h-2 rounded-full ${state.loading ? 'bg-warning animate-pulse' : 'bg-success'}`} title="Connection status" />
          </div>
        )}
      </div>
    </div>
  )
}