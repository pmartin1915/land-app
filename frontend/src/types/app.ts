// Frontend-specific types and interfaces

import { AISuggestion } from './api'

// Application State Types
export interface AppState {
  user: UserSession | null
  theme: 'light' | 'dark' | 'system'
  selectedProperties: string[]
  filters: PropertyFilters
  loading: boolean
  error: string | null
  sidebarCollapsed: boolean
  activeRoute: string
}

export interface UserSession {
  id: string
  email: string
  name: string
  preferences: UserPreferences
  permissions: string[]
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  defaultCounty?: string
  defaultFilters: PropertyFilters
  notifications: NotificationSettings
  tableColumns: string[]
  mapProvider: 'mapbox' | 'vertex'
}

export interface NotificationSettings {
  emailAlerts: boolean
  browserNotifications: boolean
  soundEnabled: boolean
  alertFrequency: 'immediate' | 'daily' | 'weekly'
}

// UI Component Types
export interface KPICard {
  id: string
  title: string
  value: string | number
  trend?: {
    direction: 'up' | 'down' | 'stable'
    percentage: number
    period: string
  }
  icon: string
  color: 'primary' | 'success' | 'warning' | 'danger'
  tooltip?: string
}

export interface ActivityItem {
  id: string
  type: 'scrape' | 'suggestion' | 'export' | 'watchlist' | 'error'
  title: string
  description: string
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface NavigationItem {
  id: string
  label: string
  icon: string
  route: string
  badge?: number
  shortcut?: string
  children?: NavigationItem[]
}

// Table and Data Grid Types
export interface TableColumn<T = unknown> {
  id: string
  label: string
  accessor: keyof T | ((item: T) => unknown)
  sortable?: boolean
  filterable?: boolean
  width?: number | string
  align?: 'left' | 'center' | 'right'
  format?: (value: unknown) => string
  render?: (value: unknown, item: T) => React.ReactNode
}

export interface TableState {
  sortBy?: string
  sortOrder: 'asc' | 'desc'
  filters: Record<string, unknown>
  selectedRows: string[]
  page: number
  pageSize: number
}

export interface TableAction<T = unknown> {
  id: string
  label: string
  icon?: string
  variant?: 'primary' | 'secondary' | 'danger'
  onClick: (items: T[]) => void
  disabled?: (items: T[]) => boolean
  bulk?: boolean
}

// Modal and Dialog Types
export interface ModalState {
  isOpen: boolean
  type: 'confirm' | 'form' | 'info' | 'error'
  title: string
  content: React.ReactNode
  actions?: ModalAction[]
  onClose?: () => void
}

export interface ModalAction {
  label: string
  variant?: 'primary' | 'secondary' | 'danger'
  onClick: () => void
  loading?: boolean
  disabled?: boolean
}

// Form Types
export interface FormField {
  name: string
  type: 'text' | 'number' | 'email' | 'password' | 'select' | 'checkbox' | 'textarea' | 'date'
  label: string
  placeholder?: string
  required?: boolean
  options?: { value: string; label: string }[]
  validation?: ValidationRule[]
  dependsOn?: string
  conditional?: (values: Record<string, unknown>) => boolean
}

export interface ValidationRule {
  type: 'required' | 'min' | 'max' | 'pattern' | 'custom'
  value?: string | number | RegExp
  message: string
  validator?: (value: unknown) => boolean
}

// Search and Filter Types
export interface SearchState {
  query: string
  filters: PropertyFilters
  activeFilters: string[]
  recentSearches: string[]
  savedSearches: SavedSearch[]
}

export interface SavedSearch {
  id: string
  name: string
  query: string
  filters: PropertyFilters
  createdAt: string
  shared: boolean
}

export interface PropertyFilters {
  priceRange?: [number, number]
  acreageRange?: [number, number]
  waterOnly?: boolean
  county?: string
  counties?: string[]
  state?: string  // State code filter: AL, AR, TX, FL
  minInvestmentScore?: number
  minYearSold?: number  // Exclude pre-X delinquencies (e.g., 2015)
  excludeDeltaRegion?: boolean  // Exclude Delta region counties (AR)
  createdAfter?: string  // ISO date string for period filter
  minCountyMarketScore?: number
  minGeographicScore?: number
  minMarketTimingScore?: number
  minTotalDescriptionScore?: number
  minRoadAccessScore?: number
  dateRange?: [string, string]
  hasDocuments?: boolean
  status?: string[]
  // Multi-state scoring filters
  maxEffectiveCost?: number  // Maximum total cost (bid + quiet title + buffer)
  minBuyHoldScore?: number   // Minimum buy & hold score (time-adjusted)
}

// Map Types
export interface MapState {
  center: [number, number]
  zoom: number
  bounds?: [[number, number], [number, number]]
  selectedProperty?: string
  clustersVisible: boolean
  heatmapVisible: boolean
  drawMode: boolean
  drawnShape?: GeoJSON.Feature
}

export interface MapLayer {
  id: string
  name: string
  type: 'cluster' | 'heatmap' | 'marker' | 'polygon'
  visible: boolean
  data: unknown[]
  style?: Record<string, unknown>
}

// Triage and AI Types
export interface TriageItem {
  id: string
  propertyId: string
  priority: 'high' | 'medium' | 'low'
  category: 'missing_data' | 'low_confidence' | 'conflict' | 'review'
  title: string
  description: string
  suggestions: AISuggestion[]
  createdAt: string
  resolvedAt?: string
  resolvedBy?: string
}

export interface TriageQueue {
  items: TriageItem[]
  counts: {
    total: number
    high: number
    medium: number
    low: number
    unresolved: number
  }
  filters: {
    priority?: string[]
    category?: string[]
    assignee?: string
  }
}

// Export Types
export interface ExportJob {
  id: string
  type: 'csv' | 'json' | 'pdf' | 'excel'
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  filters: PropertyFilters
  totalRecords: number
  exportedRecords: number
  createdAt: string
  completedAt?: string
  downloadUrl?: string
  error?: string
}

export interface ExportConfig {
  type: 'csv' | 'json' | 'pdf' | 'excel'
  filename?: string
  columns?: string[]
  filters?: PropertyFilters
  format?: {
    dateFormat?: string
    numberFormat?: string
    includeHeaders?: boolean
  }
  schedule?: {
    frequency: 'once' | 'daily' | 'weekly' | 'monthly'
    time?: string
    timezone?: string
  }
}

// Notification Types
export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  actions?: NotificationAction[]
  persistent?: boolean
  timeout?: number
  createdAt: string
  readAt?: string
}

export interface NotificationAction {
  label: string
  action: () => void
  variant?: 'primary' | 'secondary'
}

// Keyboard Shortcut Types
export interface KeyboardShortcut {
  id: string
  key: string
  description: string
  action: () => void
  global?: boolean
  category: 'navigation' | 'actions' | 'editing' | 'view'
}

// Analytics and Reporting Types
export interface AnalyticsData {
  properties: {
    total: number
    newThisWeek: number
    needsReview: number
    watchlisted: number
  }
  counties: {
    name: string
    count: number
    avgPrice: number
  }[]
  trends: {
    date: string
    newProperties: number
    avgPrice: number
    volume: number
  }[]
  performance: {
    loadTime: number
    apiResponseTime: number
    cacheHitRate: number
  }
}

export interface ChartData {
  labels: string[]
  datasets: {
    label: string
    data: number[]
    backgroundColor?: string | string[]
    borderColor?: string | string[]
    borderWidth?: number
  }[]
}

// Local Storage Types
export interface StorageData {
  theme: string
  sidebarCollapsed: boolean
  tableColumns: string[]
  recentSearches: string[]
  savedSearches: SavedSearch[]
  userPreferences: UserPreferences
  cachedData: {
    [key: string]: {
      data: unknown
      timestamp: number
      ttl: number
    }
  }
}

// Error Types
export interface AppError {
  id: string
  type: 'network' | 'validation' | 'permission' | 'system'
  message: string
  details?: string
  timestamp: string
  recoverable: boolean
  actions?: ErrorAction[]
}

export interface ErrorAction {
  label: string
  action: () => void
  variant?: 'primary' | 'secondary'
}

// Utility Types
export type LoadingState = 'idle' | 'loading' | 'succeeded' | 'failed'

export type SortOrder = 'asc' | 'desc'

export type Theme = 'light' | 'dark' | 'system'

export type ViewMode = 'table' | 'grid' | 'map'

export type PanelPosition = 'left' | 'right' | 'bottom'

export type ComponentSize = 'sm' | 'md' | 'lg' | 'xl'

export type ComponentVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger'