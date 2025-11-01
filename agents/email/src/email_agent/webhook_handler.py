"""SendGrid Webhook Handler

Receives and processes SendGrid event webhooks.

Events:
- delivered: Email was successfully delivered
- open: Email was opened
- click: Link in email was clicked
- bounce: Email bounced
- spam_report: Email was marked as spam
- unsubscribe: Recipient unsubscribed
"""
import logging
import os
from typing import List, Dict, Any
from datetime import datetime
import psycopg2
import psycopg2.extras

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SendGrid Webhook Handler",
    description="Processes SendGrid email event webhooks",
    version="1.0.0"
)


class WebhookHandler:
    """
    Processes SendGrid webhook events

    Updates email_queue table based on events
    """

    def __init__(self, database_url: str):
        """
        Initialize webhook handler

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        logger.info("WebhookHandler initialized")

    def process_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process batch of SendGrid events

        Args:
            events: List of event dictionaries from SendGrid

        Returns:
            Processing results
        """
        logger.info(f"Processing {len(events)} webhook events")

        results = {
            'total': len(events),
            'processed': 0,
            'failed': 0,
            'errors': []
        }

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            for event in events:
                try:
                    self._process_single_event(event, conn)
                    results['processed'] += 1

                except Exception as e:
                    logger.error(f"Failed to process event: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'event': event.get('event'),
                        'error': str(e)
                    })

            conn.commit()

        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

        logger.info(f"Processed {results['processed']}/{results['total']} events")

        return results

    def _process_single_event(self, event: Dict[str, Any], conn):
        """
        Process a single SendGrid event

        Args:
            event: Event dictionary from SendGrid
            conn: Database connection
        """
        event_type = event.get('event')
        sg_message_id = event.get('sg_message_id')

        if not sg_message_id:
            logger.warning(f"Event missing sg_message_id: {event_type}")
            return

        logger.info(f"Processing event: {event_type} for message {sg_message_id}")

        # Extract custom args (our tracking IDs)
        email_queue_id = event.get('email_queue_id')
        timestamp = event.get('timestamp')

        # Convert timestamp to datetime
        event_time = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

        # Update email_queue based on event type
        cursor = conn.cursor()

        if event_type == 'delivered':
            # Email was delivered
            query = """
                UPDATE email_queue
                SET status = 'delivered',
                    delivered_at = %s,
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (event_time, sg_message_id))

        elif event_type == 'open':
            # Email was opened
            query = """
                UPDATE email_queue
                SET status = 'opened',
                    opened_at = COALESCE(opened_at, %s),
                    open_count = COALESCE(open_count, 0) + 1,
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (event_time, sg_message_id))

        elif event_type == 'click':
            # Link was clicked
            url = event.get('url', '')

            query = """
                UPDATE email_queue
                SET status = 'clicked',
                    clicked_at = COALESCE(clicked_at, %s),
                    click_count = COALESCE(click_count, 0) + 1,
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (event_time, sg_message_id))

            # Log click event
            logger.info(f"Click event: {url}")

        elif event_type in ['bounce', 'dropped', 'deferred']:
            # Email bounced or was dropped
            reason = event.get('reason', '')
            bounce_type = event.get('type', '')  # hard or soft bounce

            query = """
                UPDATE email_queue
                SET status = 'bounced',
                    error_message = %s,
                    bounced_at = %s,
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (f"{bounce_type}: {reason}", event_time, sg_message_id))

            # For hard bounces, consider suppressing the email
            if bounce_type == 'hard':
                logger.warning(f"Hard bounce: {sg_message_id} - {reason}")

        elif event_type == 'spam_report':
            # Marked as spam
            query = """
                UPDATE email_queue
                SET status = 'spam',
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (sg_message_id,))

            logger.warning(f"Spam report: {sg_message_id}")

        elif event_type == 'unsubscribe':
            # Unsubscribed
            query = """
                UPDATE email_queue
                SET status = 'unsubscribed',
                    unsubscribed_at = %s,
                    updated_at = NOW()
                WHERE sendgrid_message_id = %s
            """
            cursor.execute(query, (event_time, sg_message_id))

            logger.info(f"Unsubscribe: {sg_message_id}")

        else:
            logger.debug(f"Unhandled event type: {event_type}")

        cursor.close()


# Global webhook handler instance
webhook_handler = None


def get_webhook_handler():
    """Get or create webhook handler instance"""
    global webhook_handler

    if webhook_handler is None:
        database_url = os.getenv('DB_DSN')

        if not database_url:
            raise ValueError("DB_DSN environment variable not set")

        webhook_handler = WebhookHandler(database_url)

    return webhook_handler


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sendgrid-webhook-handler"}


@app.post("/webhook/sendgrid")
async def sendgrid_webhook(request: Request):
    """
    SendGrid webhook endpoint

    Receives POST requests from SendGrid with email event data
    """
    try:
        # Parse JSON body
        events = await request.json()

        if not isinstance(events, list):
            events = [events]

        logger.info(f"Received webhook with {len(events)} events")

        # Get handler and process events
        handler = get_webhook_handler()
        results = handler.process_events(events)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "processed": results['processed'],
                "failed": results['failed']
            }
        )

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SendGrid Webhook Handler",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook/sendgrid"
        }
    }


def main():
    """Run webhook server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    port = int(os.getenv('PORT', '8000'))

    logger.info(f"Starting SendGrid webhook handler on port {port}")

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
