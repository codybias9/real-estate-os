/**
 * Property domain types matching backend contracts
 */

export enum PropertyState {
  DISCOVERED = 'discovered',
  ENRICHED = 'enriched',
  SCORED = 'scored',
  MEMO_GENERATED = 'memo_generated',
  OUTREACH_PENDING = 'outreach_pending',
  CONTACTED = 'contacted',
  RESPONDED = 'responded',
  ARCHIVED = 'archived',
}

export interface PropertyProvenance {
  source: string;
  confidence: number;
  cost_cents?: number;
  license_url?: string;
  retrieved_at: string;
}

export interface PropertyOwner {
  name?: string;
  type?: 'Person' | 'Company' | 'LLC' | 'Trust' | 'Government' | 'Unknown';
  email?: string;
  phone?: string;
  mailing_address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
  };
}

export interface Property {
  id: string;
  tenant_id: string;
  apn: string;
  apn_hash: string;

  // Address
  street?: string;
  city?: string;
  state?: string;
  zip?: string;
  county?: string;

  // Geo
  lat?: number;
  lng?: number;

  // Attributes
  beds?: number;
  baths?: number;
  sqft?: number;
  lot_sqft?: number;
  year_built?: number;
  stories?: number;
  garage_spaces?: number;
  pool?: boolean;

  // Owner
  owner?: PropertyOwner;

  // State
  state: PropertyState;
  state_updated_at: string;

  // Score
  score?: number;
  score_reasons?: ScoreReason[];

  // Timestamps
  created_at: string;
  updated_at: string;

  // Metadata
  extra_metadata?: Record<string, unknown>;
}

export interface ScoreReason {
  feature: string;
  weight: number;
  direction: 'positive' | 'negative' | 'neutral';
  note: string;
}

export interface ScoreResult {
  property_id: string;
  score: number;
  reasons: ScoreReason[];
  model_version: string;
  scored_at: string;
}
