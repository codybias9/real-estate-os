/**
 * Type definitions for Provenance API
 * Corresponds to api/app/schemas/provenance.py
 */

export interface FieldProvenanceBase {
  source_system?: string | null;
  source_url?: string | null;
  method?: 'scrape' | 'api' | 'manual' | 'computed' | null;
  confidence?: number | null;
  version: number;
  extracted_at: string;
}

export interface FieldProvenanceDetail extends FieldProvenanceBase {
  id: string;
  tenant_id: string;
  entity_type: string;
  entity_id: string;
  field_path: string;
  value: any;
  created_at: string;
}

export interface PropertyBase {
  id: string;
  tenant_id: string;
  canonical_address: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
    country?: string;
  };
  parcel?: string | null;
  lat?: number | null;
  lon?: number | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyWithProvenance extends PropertyBase {
  fields: Record<string, any>;
  provenance: Record<string, FieldProvenanceBase>;
}

export interface OwnerEntitySummary {
  id: string;
  canonical_name: string;
  entity_type?: string | null;
  tax_id?: string | null;
}

export interface PropertyOwnerLink {
  owner: OwnerEntitySummary;
  role?: string | null;
  share_pct?: number | null;
  confidence?: number | null;
  link_created_at: string;
}

export interface ScorecardSummary {
  id: string;
  score: number;
  grade: string;
  confidence?: number | null;
  model_version: string;
  scored_at: string;
}

export interface DealSummary {
  id: string;
  stage: string;
  probability?: number | null;
  expected_close_date?: string | null;
  created_at: string;
}

export interface PropertyDetail extends PropertyWithProvenance {
  owners: PropertyOwnerLink[];
  scorecards: ScorecardSummary[];
  deals: DealSummary[];
}

export interface ShapValue {
  feature: string;
  value: number;
  display_value: string;
}

export interface Driver {
  feature: string;
  contribution: number;
  explanation: string;
}

export interface Counterfactual {
  field_changes: Record<string, any>;
  new_grade: string;
  explanation: string;
}

export interface ScoreExplainabilityDetail {
  id: string;
  scorecard_id: string;
  shap_values: ShapValue[];
  top_positive_drivers: Driver[];
  top_negative_drivers: Driver[];
  counterfactuals: Counterfactual[];
  created_at: string;
}

export interface ProvenanceStatsResponse {
  total_fields: number;
  fields_with_provenance: number;
  coverage_percentage: number;
  by_source_system: Record<string, number>;
  by_method: Record<string, number>;
  avg_confidence: number;
  stale_fields: number;
}

export interface FieldHistoryResponse {
  property_id: string;
  field_path: string;
  history: FieldProvenanceDetail[];
  total_versions: number;
}

export interface EvidenceEventCreate {
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_type?: string | null;
  actor_id?: string | null;
  evidence: Record<string, any>;
  notes?: string | null;
}

export interface EvidenceEventDetail {
  id: string;
  tenant_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_type?: string | null;
  actor_id?: string | null;
  evidence: Record<string, any>;
  notes?: string | null;
  occurred_at: string;
  created_at: string;
}

// =====================================================================
// WAVE 2.3/2.4: ML-Powered Similarity Search Types
// =====================================================================

/**
 * Similar property result from ML embeddings
 */
export interface SimilarProperty {
  property_id: string;
  similarity_score: number;
  listing_price?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  property_type?: string | null;
  zipcode?: string | null;
  confidence?: number | null;
}

/**
 * Response from GET /properties/{id}/similar
 */
export interface SimilarPropertiesResponse {
  property_id: string;
  total_results: number;
  similar_properties: SimilarProperty[];
  error?: string;
}

/**
 * Response from POST /properties/recommend
 */
export interface RecommendationsResponse {
  user_id: number;
  total_results: number;
  recommendations: SimilarProperty[];
  message?: string;
}

/**
 * Response from POST /properties/{id}/feedback
 */
export interface FeedbackResponse {
  property_id: string;
  user_id: number;
  feedback: 'like' | 'dislike';
  recorded_at: string;
  message?: string;
}

// =====================================================================
// WAVE 3.1: COMP-CRITIC TYPES
// =====================================================================

/**
 * Comparable property for comp analysis
 */
export interface ComparableProperty {
  property_id: string;
  similarity_score: number;
  listing_price: number;
  price_per_sqft: number;
}

/**
 * Comp analysis result from Comp-Critic
 */
export interface CompAnalysisResponse {
  property_id: string;
  subject_price: number;
  subject_price_per_sqft: number;

  // Comp statistics
  num_comps: number;
  avg_comp_price: number;
  avg_comp_price_per_sqft: number;

  // Market position
  market_position: 'overvalued' | 'fairly_valued' | 'undervalued';
  price_deviation_percent: number;

  // Negotiation
  negotiation_leverage: number;
  negotiation_strategy: 'aggressive' | 'moderate' | 'cautious';
  recommended_offer_range: {
    min: number;
    max: number;
  };

  // Comps
  comps: ComparableProperty[];

  // Insights
  recommendations: string[];
  risk_factors: string[];
  opportunities: string[];

  // Error handling
  error?: string;
}

// =====================================================================
// WAVE 3.2: NEGOTIATION BRAIN TYPES
// =====================================================================

/**
 * Talking point for negotiation leverage
 */
export interface TalkingPoint {
  category: string;
  point: string;
  evidence: string;
  weight: number;
}

/**
 * Counter-offer strategy details
 */
export interface CounterOfferStrategy {
  initial_counter_max_increase: number;
  walk_away_price: number;
  concession_strategy: string;
  alternative_concessions: string[];
}

/**
 * Deal structure recommendations
 */
export interface DealStructure {
  contingencies: string[];
  inspection_period_days: number;
  closing_timeline_days: number;
  earnest_money_percent: number;
  escalation_clause: boolean;
  appraisal_gap_coverage?: number | null;
  seller_concessions_target?: number | null;
}

/**
 * Negotiation strategy response from Negotiation Brain
 */
export interface NegotiationStrategyResponse {
  property_id: string;

  // Strategy
  strategy: string; // aggressive/moderate/cautious/walk_away
  strategy_confidence: number;
  strategy_rationale: string;

  // Offers
  recommended_initial_offer: number;
  recommended_max_offer: number;
  walk_away_price: number;
  offer_justification: string;

  // Market context
  market_condition: string;
  seller_motivation: string;

  // Tactical guidance
  talking_points: TalkingPoint[];
  counter_offer_strategy: CounterOfferStrategy;
  deal_structure: DealStructure;

  // Risks and opportunities
  key_risks: string[];
  key_opportunities: string[];

  // Timeline
  recommended_response_time: string;

  // Metadata
  created_at: string;

  // Error handling
  error?: string;
}
