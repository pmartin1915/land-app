// TypeScript interfaces matching SQLAlchemy models exactly
// Based on backend_api/database/models.py

export type UUID = string

/**
 * Property interface matching SQLAlchemy Property model exactly.
 * All field names and types must remain compatible with backend API.
 */
export interface Property {
  // Primary key
  id: UUID

  // Core property data
  parcel_id: string
  amount: number
  acreage?: number
  price_per_acre?: number

  // Calculated algorithm fields - MUST use exact backend algorithms
  water_score: number
  investment_score?: number
  estimated_all_in_cost?: number

  // Multi-state scoring fields
  buy_hold_score?: number  // Time-adjusted investment score for buy & hold strategy
  effective_cost?: number  // Total cost including quiet title and buffer
  wholesale_score?: number // Score for wholesale flip strategy
  is_market_reject?: boolean  // Pre-2015 delinquency marker (market rejected)
  is_delta_region?: boolean   // Arkansas Delta region indicator (economically distressed)

  // Enhanced Description Intelligence Fields (Phase 1 Enhancement)
  lot_dimensions_score: number
  shape_efficiency_score: number
  corner_lot_bonus: number
  irregular_shape_penalty: number
  subdivision_quality_score: number
  road_access_score: number
  location_type_score: number
  title_complexity_score: number
  survey_requirement_score: number
  premium_water_access_score: number
  total_description_score: number

  // County Intelligence Fields
  county_market_score: number
  geographic_score: number
  market_timing_score: number

  // Financial data
  assessed_value?: number
  assessed_value_ratio?: number

  // Property details
  description?: string
  county?: string
  state: string  // State code: AL, AR, TX, FL
  owner_name?: string
  year_sold?: string

  // Ranking and metadata
  rank?: number
  created_at: string
  updated_at?: string

  // Sync metadata for cross-platform compatibility
  device_id?: string
  sync_timestamp?: string | null
  is_deleted: boolean
}

/**
 * County interface with ADOR alphabetical mapping.
 * CRITICAL: Must use exact same mapping as backend models.
 */
export interface County {
  // Use ADOR alphabetical codes (NOT FIPS codes)
  code: string // ADOR alphabetical county code (01-67)
  name: string // County name
  created_at: string
  updated_at: string
}

/**
 * AI Suggestion interface for property corrections and improvements.
 */
export interface AISuggestion {
  id: UUID
  parcel_id: UUID
  field: string // 'auctionDate', 'owner', etc.
  proposed_value: string | number | boolean | null
  confidence: number // 0-100
  reason?: string // brief explanation
  source_ids: UUID[] // provenance references
  created_at: string
  applied_by?: string // user id
  applied_at?: string
}

/**
 * Source snapshot for data provenance.
 */
export interface SourceSnapshot {
  id: UUID
  source_name: string
  scraped_at: string
  raw_html?: string
  extracted_fields: Record<string, unknown>
  url?: string
}

/**
 * Transaction interface for financial tracking.
 */
export interface Transaction {
  id: UUID
  parcel_id: UUID
  date: string // ISO
  description: string
  amount?: number
  source?: string
  raw?: Record<string, unknown>
}

/**
 * Sync operation logging for debugging and monitoring.
 */
export interface SyncLog {
  id: UUID
  device_id: string
  operation: string // 'delta', 'full', 'upload', 'download'
  status: string // 'success', 'failed', 'partial'

  // Sync metrics
  records_processed: number
  conflicts_detected: number
  conflicts_resolved: number

  // Timing data
  started_at: string
  completed_at?: string
  duration_seconds?: number

  // Error information
  error_message?: string

  // Algorithm validation
  algorithm_validation_passed: boolean
}

/**
 * User profile for application assistance.
 */
export interface UserProfile {
  id: UUID

  // Personal information
  full_name: string
  email: string
  phone: string
  address: string
  city: string
  state: string
  zip_code: string

  // Investment preferences
  max_investment_amount?: number
  min_acreage?: number
  max_acreage?: number
  preferred_counties?: string // JSON list of preferred counties

  // Metadata
  created_at: string
  updated_at: string
  is_active: boolean
}

/**
 * Property application tracking for organizing data for manual form submission.
 */
export interface PropertyApplication {
  id: UUID
  user_profile_id: string
  property_id: string

  // State form data
  cs_number?: string
  parcel_number: string
  sale_year: string
  county: string
  description: string
  assessed_name?: string

  // Financial data
  amount: number
  acreage?: number
  investment_score?: number
  estimated_total_cost?: number
  roi_estimate?: number

  // Application status
  status: string // 'draft', 'submitted', 'completed', etc.
  notes?: string

  // Price tracking
  price_request_date?: string
  price_received_date?: string
  final_price?: number

  // Metadata
  created_at: string
  updated_at: string
}

/**
 * Batch of applications for processing efficiency.
 */
export interface ApplicationBatch {
  id: UUID
  user_profile_id: string
  batch_name?: string

  // Financial summary
  total_estimated_investment?: number

  // Processing tracking
  forms_generated: number
  applications_submitted: number
  prices_received: number

  // Status
  status: string // 'draft', 'processing', 'completed'

  // Metadata
  created_at: string
  updated_at: string
}

/**
 * Notification tracking for application process.
 */
export interface ApplicationNotification {
  id: UUID
  user_profile_id: string
  property_id?: string

  // Notification details
  notification_type: string
  title: string
  message: string

  // State communication tracking
  state_email_expected: boolean
  state_email_received: boolean
  price_amount?: number

  // User interaction
  read_at?: string
  action_required: boolean
  action_deadline?: string

  // Metadata
  created_at: string
}

// API Response Types
export interface APIResponse<T> {
  data: T
  message?: string
  timestamp: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

export interface APIError {
  error: string
  message: string
  timestamp: string
  path?: string
  ai_recovery_hint?: string
  details?: {
    message?: string
    [key: string]: unknown
  }
}

// Filter and Search Types
export interface PropertyFilters {
  price_range?: [number, number]
  acreage_range?: [number, number]
  water_only?: boolean
  county?: string
  state?: string  // State code filter: AL, AR, TX, FL
  min_investment_score?: number
  min_year_sold?: number  // Exclude pre-X delinquencies (e.g., 2015)
  min_county_market_score?: number
  min_geographic_score?: number
  min_market_timing_score?: number
  min_total_description_score?: number
  min_road_access_score?: number
}

export interface SearchParams {
  q?: string
  filters?: PropertyFilters
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  per_page?: number
}

// CSV Import Types
export interface CSVImportMapping {
  parcel_id?: string
  amount?: string
  acreage?: string
  county?: string
  state?: string
  description?: string
  owner_name?: string
  year_sold?: string
  assessed_value?: string
  sale_type?: string
  redemption_period_days?: string
  auction_date?: string
  auction_platform?: string
  data_source?: string
  estimated_market_value?: string
}

export interface CSVImportPreview {
  headers: string[]
  rows: string[][]
  total_rows: number
  suggested_mapping: Record<string, string | null>
  unmapped_headers: string[]
  potential_duplicates: number
}

export interface CSVImportRowError {
  row: number
  field?: string
  error: string
}

export interface CSVImportResult {
  imported: number
  skipped_duplicates: number
  errors: number
  failed_rows: CSVImportRowError[]
}

// Map and Geocoding Types
export interface GeocodeResult {
  lat: number
  lng: number
  address: string
  confidence: number
  geocoded_at: string
}

export interface MapCluster {
  id: string
  lat: number
  lng: number
  count: number
  properties: Property[]
}

// Cache and Performance Types
export interface CacheStats {
  hits: number
  misses: number
  size: number
  hit_ratio: number
}

export interface PerformanceMetrics {
  load_time: number
  memory_usage: number
  cache_stats: CacheStats
  api_response_time: number
}