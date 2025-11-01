"""Email Agent - Sends investor memos via SendGrid

Orchestrates email campaigns for property outreach.

Workflow:
1. Fetch action packets (properties with PDFs ready)
2. Fetch investor/lead contacts from database
3. Generate personalized email content
4. Download PDF from MinIO
5. Send email via SendGrid with PDF attachment
6. Track email in email_queue table
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras
import json

from .sendgrid_client import SendGridClient
from .email_templates import EmailTemplates

logger = logging.getLogger(__name__)


class EmailAgent:
    """
    Email outreach agent

    Manages email campaigns for investor memos.
    """

    def __init__(
        self,
        database_url: str,
        sendgrid_api_key: str,
        from_email: str,
        from_name: str = "Real Estate OS",
        minio_client=None
    ):
        """
        Initialize email agent

        Args:
            database_url: PostgreSQL connection string
            sendgrid_api_key: SendGrid API key
            from_email: Sender email address
            from_name: Sender name
            minio_client: MinIO client for PDF downloads (optional)
        """
        self.database_url = database_url
        self.minio_client = minio_client

        # Initialize SendGrid client
        self.sendgrid = SendGridClient(
            api_key=sendgrid_api_key,
            from_email=from_email,
            from_name=from_name
        )

        # Initialize email templates
        self.templates = EmailTemplates()

        logger.info("EmailAgent initialized")

    def send_campaign(
        self,
        campaign_id: int,
        max_emails: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send email campaign

        Args:
            campaign_id: Campaign ID to send
            max_emails: Maximum emails to send (for testing)

        Returns:
            Dictionary with campaign results
        """
        logger.info(f"Starting email campaign: {campaign_id}")

        results = {
            'campaign_id': campaign_id,
            'total': 0,
            'sent': 0,
            'failed': 0,
            'errors': []
        }

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            # Get campaign details
            campaign = self._get_campaign(campaign_id, conn)

            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return results

            # Get pending emails for campaign
            pending_emails = self._get_pending_emails(campaign_id, max_emails, conn)

            results['total'] = len(pending_emails)

            logger.info(f"Found {len(pending_emails)} pending emails")

            # Send each email
            for email_queue_id, recipient_email, recipient_name, action_packet_id in pending_emails:
                try:
                    success = self._send_single_email(
                        email_queue_id=email_queue_id,
                        recipient_email=recipient_email,
                        recipient_name=recipient_name,
                        action_packet_id=action_packet_id,
                        campaign_id=campaign_id,
                        conn=conn
                    )

                    if success:
                        results['sent'] += 1
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Failed to send email {email_queue_id}: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'email_queue_id': email_queue_id,
                        'error': str(e)
                    })

            conn.commit()

        except Exception as e:
            logger.error(f"Campaign send error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

        logger.info(f"Campaign {campaign_id} complete: {results['sent']}/{results['total']} sent")

        return results

    def _send_single_email(
        self,
        email_queue_id: int,
        recipient_email: str,
        recipient_name: str,
        action_packet_id: int,
        campaign_id: int,
        conn
    ) -> bool:
        """
        Send a single email

        Args:
            email_queue_id: Email queue record ID
            recipient_email: Recipient email
            recipient_name: Recipient name
            action_packet_id: Action packet ID
            campaign_id: Campaign ID
            conn: Database connection

        Returns:
            True if sent successfully
        """
        logger.info(f"Sending email to: {recipient_email}")

        # Mark as sending
        self._update_email_status(email_queue_id, 'sending', conn)

        try:
            # Get action packet data
            action_packet = self._get_action_packet(action_packet_id, conn)

            if not action_packet:
                logger.error(f"Action packet {action_packet_id} not found")
                self._update_email_status(email_queue_id, 'error', conn,
                                         error_message="Action packet not found")
                return False

            # Get property data for email template
            property_data = self._get_property_data_for_email(action_packet['prospect_id'], conn)

            if not property_data:
                logger.error(f"Property data not found for prospect {action_packet['prospect_id']}")
                self._update_email_status(email_queue_id, 'error', conn,
                                         error_message="Property data not found")
                return False

            # Render email content
            email_content = self.templates.render_investor_memo_email(property_data)

            # Download PDF from MinIO (if client provided)
            pdf_bytes = None
            if self.minio_client and action_packet.get('pdf_url'):
                try:
                    # Extract object name from metadata
                    metadata = action_packet.get('metadata', {})
                    object_name = metadata.get('object_name')

                    if object_name:
                        pdf_bytes = self.minio_client.download_pdf(object_name)
                        logger.info(f"Downloaded PDF: {object_name}")
                except Exception as e:
                    logger.warning(f"Failed to download PDF: {e}")

            # Send email via SendGrid
            send_result = self.sendgrid.send_investor_memo(
                to_email=recipient_email,
                to_name=recipient_name,
                subject=email_content['subject'],
                html_body=email_content['html'],
                plain_body=email_content['plain'],
                pdf_attachment=pdf_bytes,
                pdf_filename=f"investment_opportunity_{action_packet['prospect_id']}.pdf",
                custom_args={
                    'email_queue_id': str(email_queue_id),
                    'action_packet_id': str(action_packet_id),
                    'campaign_id': str(campaign_id),
                    'prospect_id': str(action_packet['prospect_id'])
                }
            )

            if send_result.get('success'):
                # Update email status
                self._update_email_status(
                    email_queue_id, 'sent', conn,
                    sendgrid_message_id=send_result.get('message_id'),
                    sent_at=datetime.now()
                )

                logger.info(f"Email sent successfully to {recipient_email}")
                return True
            else:
                # Update error status
                self._update_email_status(
                    email_queue_id, 'error', conn,
                    error_message=send_result.get('error', 'Unknown error')
                )

                logger.error(f"Failed to send email to {recipient_email}")
                return False

        except Exception as e:
            logger.error(f"Send email error: {e}")
            self._update_email_status(email_queue_id, 'error', conn, error_message=str(e))
            return False

    def _get_campaign(self, campaign_id: int, conn) -> Optional[Dict]:
        """Get campaign details"""
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT * FROM email_campaigns WHERE id = %s",
            (campaign_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        return dict(result) if result else None

    def _get_pending_emails(self, campaign_id: int, limit: Optional[int], conn) -> List[tuple]:
        """Get pending emails for campaign"""
        cursor = conn.cursor()

        query = """
            SELECT id, recipient_email, recipient_name, action_packet_id
            FROM email_queue
            WHERE campaign_id = %s
              AND status = 'pending'
            ORDER BY created_at ASC
        """

        params = [campaign_id]

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()

        return results

    def _get_action_packet(self, action_packet_id: int, conn) -> Optional[Dict]:
        """Get action packet details"""
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT * FROM action_packets WHERE id = %s",
            (action_packet_id,)
        )
        result = cursor.fetchone()
        cursor.close()

        if result:
            # Parse metadata JSON
            result_dict = dict(result)
            if result_dict.get('metadata'):
                result_dict['metadata'] = json.loads(result_dict['metadata']) \
                    if isinstance(result_dict['metadata'], str) else result_dict['metadata']
            return result_dict

        return None

    def _get_property_data_for_email(self, prospect_id: int, conn) -> Optional[Dict]:
        """Get property data for email template"""
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT
                pq.url as listing_url,
                pq.payload->>'address' as address,
                pq.payload->>'city' as city,
                pq.payload->>'state' as state,
                pq.payload->>'price' as listing_price,
                pe.bedrooms,
                pe.bathrooms,
                ps.bird_dog_score as score
            FROM prospect_queue pq
            LEFT JOIN property_enrichment pe ON pe.prospect_id = pq.id
            LEFT JOIN property_scores ps ON ps.prospect_id = pq.id
            WHERE pq.id = %s
        """

        cursor.execute(query, (prospect_id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            data = dict(result)
            # Convert listing_price to float
            if data.get('listing_price'):
                try:
                    data['listing_price'] = float(data['listing_price'])
                except:
                    data['listing_price'] = 0

            # Add calculated potential ROI (simplified)
            data['potential_roi'] = min(100, max(0, (data.get('score', 0) / 75) * 15))

            return data

        return None

    def _update_email_status(
        self,
        email_queue_id: int,
        status: str,
        conn,
        sendgrid_message_id: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ):
        """Update email queue status"""
        cursor = conn.cursor()

        query = """
            UPDATE email_queue
            SET status = %s,
                sendgrid_message_id = COALESCE(%s, sendgrid_message_id),
                sent_at = COALESCE(%s, sent_at),
                error_message = COALESCE(%s, error_message),
                updated_at = NOW()
            WHERE id = %s
        """

        cursor.execute(query, (
            status,
            sendgrid_message_id,
            sent_at,
            error_message,
            email_queue_id
        ))

        cursor.close()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Email Outreach Agent")
    parser.add_argument('--campaign-id', type=int, required=True,
                       help='Campaign ID to send')
    parser.add_argument('--db-dsn', type=str, default=os.getenv('DB_DSN'),
                       help='Database connection string')
    parser.add_argument('--sendgrid-api-key', type=str, default=os.getenv('SENDGRID_API_KEY'),
                       help='SendGrid API key')
    parser.add_argument('--from-email', type=str, default=os.getenv('FROM_EMAIL'),
                       help='Sender email address')
    parser.add_argument('--from-name', type=str, default='Real Estate OS',
                       help='Sender name')
    parser.add_argument('--max-emails', type=int,
                       help='Maximum emails to send (for testing)')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize agent
    agent = EmailAgent(
        database_url=args.db_dsn,
        sendgrid_api_key=args.sendgrid_api_key,
        from_email=args.from_email,
        from_name=args.from_name
    )

    # Run campaign
    results = agent.send_campaign(
        campaign_id=args.campaign_id,
        max_emails=args.max_emails
    )

    print(f"\nEmail Campaign Results:")
    print(f"  Total: {results['total']}")
    print(f"  Sent: {results['sent']}")
    print(f"  Failed: {results['failed']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  Email {error['email_queue_id']}: {error['error']}")


if __name__ == "__main__":
    main()
