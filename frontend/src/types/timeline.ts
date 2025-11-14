/**
 * Timeline and collaboration types
 */

export enum EventType {
  // System events
  PROPERTY_DISCOVERED = 'property_discovered',
  PROPERTY_ENRICHED = 'property_enriched',
  PROPERTY_SCORED = 'property_scored',
  MEMO_GENERATED = 'memo_generated',
  OUTREACH_SENT = 'outreach_sent',
  OUTREACH_OPENED = 'outreach_opened',
  OUTREACH_CLICKED = 'outreach_clicked',
  OUTREACH_BOUNCED = 'outreach_bounced',
  STATE_CHANGED = 'state_changed',

  // User events
  COMMENT_ADDED = 'comment_added',
  NOTE_ADDED = 'note_added',
  NOTE_UPDATED = 'note_updated',
  ATTACHMENT_ADDED = 'attachment_added',
  TAG_ADDED = 'tag_added',
  TAG_REMOVED = 'tag_removed',
  ASSIGNED = 'assigned',
  UNASSIGNED = 'unassigned',
}

export interface TimelineEvent {
  id: string;
  tenant_id: string;
  property_id: string;
  event_type: EventType;
  title: string;
  content?: string;
  content_html?: string;
  event_source?: string;
  event_data?: Record<string, unknown>;
  correlation_id?: string;
  user_id?: string;
  user_name?: string;
  attachments?: string[];
  tags?: string[];
  is_system_event: boolean;
  created_at: string;
  deleted_at?: string;
}

export interface TimelineNote {
  id: string;
  tenant_id: string;
  property_id: string;
  user_id: string;
  user_name: string;
  title: string;
  content: string;
  content_html?: string;
  is_private: boolean;
  attachments?: string[];
  created_at: string;
  updated_at: string;
  deleted_at?: string;
}

export interface TimelineStatistics {
  [key: string]: number;
}
