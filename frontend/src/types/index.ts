// ============================================================================
// USER & AUTHENTICATION
// ============================================================================

export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  team_id: number
  is_active: boolean
  created_at: string
  last_login: string | null
}

export type UserRole = 'admin' | 'manager' | 'agent' | 'viewer'

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  full_name: string
  team_name: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
  user: User
}

// ============================================================================
// PROPERTIES
// ============================================================================

export type PropertyStage =
  | 'new'
  | 'outreach'
  | 'qualified'
  | 'negotiation'
  | 'under_contract'
  | 'closed_won'
  | 'closed_lost'
  | 'archived'

export interface Property {
  id: number
  team_id: number
  address: string
  city: string
  state: string
  zip_code: string
  latitude: number | null
  longitude: number | null
  apn: string | null
  owner_name: string | null
  bird_dog_score: number
  current_stage: PropertyStage
  previous_stage: PropertyStage | null
  stage_changed_at: string
  assigned_user_id: number | null
  tags: string[]
  notes: string | null
  last_contact_at: string | null
  memo_generated_at: string | null
  memo_content: string | null
  custom_fields: Record<string, any>
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface CreatePropertyData {
  team_id: number
  address: string
  city: string
  state: string
  zip_code: string
  assigned_user_id?: number
  tags?: string[]
  notes?: string
}

export interface UpdatePropertyData {
  current_stage?: PropertyStage
  assigned_user_id?: number
  tags?: string[]
  notes?: string
  custom_fields?: Record<string, any>
}

// ============================================================================
// TIMELINE
// ============================================================================

export interface TimelineEvent {
  id: number
  property_id: number
  event_type: string
  event_title: string
  event_description: string
  metadata: Record<string, any> | null
  created_at: string
  created_by_user_id: number | null
}

// ============================================================================
// COMMUNICATIONS
// ============================================================================

export interface Communication {
  id: number
  property_id: number
  direction: 'inbound' | 'outbound'
  channel: 'email' | 'sms' | 'call' | 'mail'
  subject: string | null
  content: string
  from_address: string
  to_address: string
  status: 'queued' | 'sent' | 'delivered' | 'failed' | 'bounced'
  external_id: string | null
  template_id: number | null
  metadata: Record<string, any> | null
  created_at: string
}

// ============================================================================
// TASKS
// ============================================================================

export interface Task {
  id: number
  property_id: number
  assigned_user_id: number | null
  task_type: string
  title: string
  description: string | null
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  due_date: string | null
  completed_at: string | null
  created_at: string
}

// ============================================================================
// TEMPLATES
// ============================================================================

export interface Template {
  id: number
  team_id: number
  name: string
  channel: 'email' | 'sms' | 'mail'
  applicable_stages: PropertyStage[]
  subject_template: string | null
  body_template: string
  variables: string[]
  is_active: boolean
  usage_count: number
  success_rate: number
  avg_response_time_hours: number | null
  created_at: string
}

// ============================================================================
// DEALS
// ============================================================================

export interface Deal {
  id: number
  property_id: number
  offer_amount: number | null
  estimated_arv: number | null
  estimated_repair_cost: number | null
  expected_profit: number | null
  profit_margin: number | null
  investor_id: number | null
  projected_close_date: string | null
  probability_of_close: number | null
  status: 'pending' | 'accepted' | 'rejected' | 'in_escrow' | 'closed'
  created_at: string
}

// ============================================================================
// INVESTORS
// ============================================================================

export interface Investor {
  id: number
  team_id: number
  name: string
  email: string | null
  phone: string | null
  investment_criteria: Record<string, any> | null
  preferred_markets: string[]
  capital_available: number | null
  is_active: boolean
  created_at: string
}

// ============================================================================
// STATS & METRICS
// ============================================================================

export interface PipelineStats {
  team_id: number
  stage_counts: Record<PropertyStage, number>
  total_properties: number
  avg_bird_dog_score: number
  properties_needing_contact: number
  properties_with_memo: number
  properties_with_reply: number
  total_estimated_value: number
}

export interface PortfolioMetrics {
  total_properties: number
  total_deal_value: number
  avg_deal_size: number
  win_rate: number
  avg_days_to_close: number
  pipeline_by_stage: Record<PropertyStage, number>
  top_performers: Array<{
    user_id: number
    user_name: string
    deals_closed: number
    total_value: number
  }>
}

// ============================================================================
// NEXT BEST ACTION
// ============================================================================

export interface NextBestAction {
  property_id: number
  action_type:
    | 'send_outreach'
    | 'follow_up'
    | 'generate_memo'
    | 'review_reply'
    | 'schedule_call'
    | 'update_stage'
    | 'enrich_data'
  priority: number
  reason: string
  context: Record<string, any>
  estimated_time_minutes: number
}

// ============================================================================
// SMART LISTS
// ============================================================================

export interface SmartList {
  id: number
  team_id: number
  name: string
  description: string | null
  filters: Record<string, any>
  is_favorite: boolean
  created_by_user_id: number
  created_at: string
}

// ============================================================================
// API RESPONSES
// ============================================================================

export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}
