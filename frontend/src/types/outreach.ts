/**
 * Outreach campaign types
 */

export enum OutreachStatus {
  DRAFT = 'draft',
  SCHEDULED = 'scheduled',
  SENT = 'sent',
  DELIVERED = 'delivered',
  OPENED = 'opened',
  CLICKED = 'clicked',
  REPLIED = 'replied',
  BOUNCED = 'bounced',
  FAILED = 'failed',
}

export interface OutreachCampaign {
  id: string;
  tenant_id: string;
  property_id: string;
  owner_name: string;
  owner_email: string;
  subject: string;
  memo_url: string;
  status: OutreachStatus;
  sendgrid_message_id?: string;
  sent_at?: string;
  delivered_at?: string;
  opened_at?: string;
  clicked_at?: string;
  bounced_at?: string;
  created_at: string;
  updated_at: string;
}
