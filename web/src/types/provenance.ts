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
