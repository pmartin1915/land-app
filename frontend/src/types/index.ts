// Export all type definitions

// API and backend types
export type {
  UUID,
  Property,
  County,
  AISuggestion,
  SourceSnapshot,
  Transaction,
  SyncLog,
  UserProfile,
  PropertyApplication,
  ApplicationBatch,
  ApplicationNotification,
  APIResponse,
  PaginatedResponse,
  APIError,
  PropertyFilters as APIPropertyFilters,
  SearchParams,
  CSVImportMapping,
  CSVImportPreview,
  CSVImportResult,
  GeocodeResult,
  MapCluster,
  CacheStats,
  PerformanceMetrics,
} from './api'

// Frontend application types
export type {
  AppState,
  UserSession,
  UserPreferences,
  NotificationSettings,
  KPICard,
  ActivityItem,
  NavigationItem,
  TableColumn,
  TableState,
  TableAction,
  ModalState,
  ModalAction,
  FormField,
  ValidationRule,
  SearchState,
  SavedSearch,
  PropertyFilters,
  MapState,
  MapLayer,
  TriageItem,
  TriageQueue,
  ExportJob,
  ExportConfig,
  Notification,
  NotificationAction,
  KeyboardShortcut,
  AnalyticsData,
  ChartData,
  StorageData,
  AppError,
  ErrorAction,
  LoadingState,
  SortOrder,
  Theme,
  ViewMode,
  PanelPosition,
  ComponentSize,
  ComponentVariant,
} from './app'

// Electron types
export type {
  ElectronAPI,
} from './electron'

// Portfolio Analytics types
export type {
  PortfolioSummaryResponse,
  CountyBreakdown,
  StateBreakdown,
  GeographicBreakdownResponse,
  ScoreBucket,
  ScoreDistributionResponse,
  ConcentrationRisk,
  RiskAnalysisResponse,
  StarRatingBreakdown,
  RecentAddition,
  PerformanceTrackingResponse,
  PortfolioAnalyticsExport,
} from './portfolio'

// Re-export commonly used types with aliases for convenience
export type {
  Property as PropertyData,
} from './api'
export type {
  PropertyFilters as Filters,
  AppState as ApplicationState,
  TableColumn as Column,
} from './app'