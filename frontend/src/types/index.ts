/**
 * TypeScript types for Real Estate OS
 */

export interface Property {
  id: number;
  source: string;
  source_id: string;
  url?: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  county?: string;
  latitude?: number;
  longitude?: number;
  property_type: string;
  price: number;
  bedrooms?: number;
  bathrooms?: number;
  sqft?: number;
  lot_size?: number;
  year_built?: number;
  listing_date?: string;
  description?: string;
  features?: string[];
  images?: string[];
  status: string;
  metadata?: any;
  created_at: string;
  updated_at: string;
}

export interface PropertyEnrichment {
  id: number;
  property_id: number;
  apn?: string;
  tax_assessment_value?: number;
  tax_assessment_year?: number;
  annual_tax_amount?: number;
  owner_name?: string;
  owner_type?: string;
  last_sale_date?: string;
  last_sale_price?: number;
  school_district?: string;
  school_rating?: number;
  walkability_score?: number;
  transit_score?: number;
  bike_score?: number;
  crime_rate?: string;
  crime_index?: number;
  median_home_value?: number;
  appreciation_1yr?: number;
  appreciation_5yr?: number;
  median_rent?: number;
  nearby_parks?: string[];
  nearby_shopping?: string[];
  flood_zone?: string;
  hoa_fees?: number;
  created_at: string;
  updated_at: string;
}

export interface PropertyScore {
  id: number;
  property_id: number;
  total_score: number;
  score_breakdown: {
    price_score: number;
    market_timing_score: number;
    investment_metrics_score: number;
    location_quality_score: number;
    property_condition_score: number;
  };
  features: {
    price_below_market_pct?: number;
    estimated_rental_yield?: number;
    equity_opportunity_pct?: number;
    neighborhood_appreciation_5yr?: number;
  };
  recommendation: string;
  recommendation_reason: string;
  risk_level: string;
  risk_factors: string[];
  model_version: string;
  scoring_method: string;
  confidence_score: number;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  properties: {
    total: number;
    new: number;
    enriched: number;
    scored: number;
    documented: number;
    recent_30_days: number;
  };
  scoring: {
    total_scored: number;
    average_score: number;
    high_score_count: number;
  };
  campaigns: {
    total: number;
    active: number;
  };
}

export interface PipelineStage {
  name: string;
  count: number;
  percentage: number;
}

export interface Campaign {
  id: number;
  name: string;
  description?: string;
  subject: string;
  status: string;
  total_recipients: number;
  emails_sent: number;
  emails_delivered: number;
  emails_opened: number;
  emails_clicked: number;
  created_at: string;
  updated_at: string;
}
