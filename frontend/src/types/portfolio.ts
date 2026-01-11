// Portfolio Analytics API types
// Matches backend models in backend_api/models/portfolio.py

// ============================================================================
// Portfolio Summary Types
// ============================================================================

export interface PortfolioSummaryResponse {
  total_count: number
  total_value: number
  total_acreage: number
  total_effective_cost: number
  avg_investment_score: number
  avg_buy_hold_score: number | null
  avg_wholesale_score: number | null
  avg_price_per_acre: number
  capital_budget: number | null
  capital_utilized: number
  capital_utilization_pct: number | null
  capital_remaining: number | null
  properties_with_water: number
  water_access_percentage: number
  timestamp: string
}

// ============================================================================
// Geographic Breakdown Types
// ============================================================================

export interface CountyBreakdown {
  county: string
  state: string
  count: number
  total_value: number
  avg_investment_score: number
  percentage_of_portfolio: number
}

export interface StateBreakdown {
  state: string
  state_name: string
  count: number
  total_value: number
  total_acreage: number
  avg_investment_score: number
  avg_buy_hold_score: number | null
  percentage_of_portfolio: number
  counties: CountyBreakdown[]
}

export interface GeographicBreakdownResponse {
  total_states: number
  total_counties: number
  states: StateBreakdown[]
  top_state: string | null
  top_county: string | null
  timestamp: string
}

// ============================================================================
// Score Distribution Types
// ============================================================================

export interface ScoreBucket {
  range_label: string
  min_score: number
  max_score: number
  count: number
  percentage: number
  property_ids: string[]
}

export interface ScoreDistributionResponse {
  investment_score_buckets: ScoreBucket[]
  buy_hold_score_buckets: ScoreBucket[]
  top_performers_count: number
  top_performers: string[]
  underperformers_count: number
  underperformers: string[]
  median_investment_score: number | null
  score_std_deviation: number | null
  timestamp: string
}

// ============================================================================
// Risk Analysis Types
// ============================================================================

export interface ConcentrationRisk {
  highest_state_concentration: number
  highest_state: string | null
  highest_county_concentration: number
  highest_county: string | null
  diversification_score: number
}

export interface RiskAnalysisResponse {
  concentration: ConcentrationRisk
  avg_time_to_ownership_days: number | null
  properties_over_1_year: number
  properties_over_3_years: number
  delta_region_count: number
  delta_region_percentage: number
  delta_region_counties: string[]
  market_reject_count: number
  market_reject_percentage: number
  largest_single_property_pct: number
  top_3_properties_pct: number
  overall_risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_flags: string[]
  timestamp: string
}

// ============================================================================
// Performance Tracking Types
// ============================================================================

export interface StarRatingBreakdown {
  rating: number
  count: number
  avg_investment_score: number
}

export interface RecentAddition {
  property_id: string
  parcel_id: string
  county: string | null
  state: string
  amount: number
  investment_score: number | null
  added_at: string
}

export interface PerformanceTrackingResponse {
  additions_last_7_days: number
  additions_last_30_days: number
  recent_additions: RecentAddition[]
  star_rating_breakdown: StarRatingBreakdown[]
  rated_count: number
  unrated_count: number
  avg_star_rating: number | null
  has_first_deal: boolean
  first_deal_stage: string | null
  first_deal_property_id: string | null
  activity_by_week: Record<string, number>
  timestamp: string
}

// ============================================================================
// Full Export Type
// ============================================================================

export interface PortfolioAnalyticsExport {
  summary: PortfolioSummaryResponse
  geographic: GeographicBreakdownResponse
  scores: ScoreDistributionResponse
  risk: RiskAnalysisResponse
  performance: PerformanceTrackingResponse
  exported_at: string
}
