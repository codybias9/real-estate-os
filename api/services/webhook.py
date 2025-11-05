"""Webhook service for sending outgoing webhooks."""

import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime

from ..database import SessionLocal
from ..models import WebhookLog


class WebhookService:
    """Webhook service for sending HTTP callbacks to external systems."""

    def __init__(self):
        """Initialize webhook service."""
        self.timeout = 30.0  # 30 seconds
        self.max_retries = 3

    async def send_webhook(
        self,
        url: str,
        event_type: str,
        payload: Dict[str, Any],
        organization_id: int,
        retry_count: int = 0,
    ) -> bool:
        """
        Send a webhook to an external URL.

        Args:
            url: Webhook endpoint URL
            event_type: Type of event (e.g., 'property.created', 'lead.updated')
            payload: Event payload data
            organization_id: Organization ID for logging
            retry_count: Current retry attempt number

        Returns:
            True if sent successfully, False otherwise
        """
        db = SessionLocal()
        webhook_log = None

        try:
            # Prepare webhook payload
            webhook_payload = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload,
            }

            # Create webhook log
            webhook_log = WebhookLog(
                organization_id=organization_id,
                event_type=event_type,
                url=url,
                payload=json.dumps(webhook_payload),
                retry_count=retry_count,
            )
            db.add(webhook_log)
            db.flush()

            # Send webhook
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "RealEstateOS-Webhook/1.0",
                        "X-Webhook-Event": event_type,
                    },
                )

                # Update webhook log
                webhook_log.status_code = response.status_code
                webhook_log.response = response.text[:1000]  # Limit response size

                if response.status_code >= 200 and response.status_code < 300:
                    webhook_log.success = True
                    db.commit()
                    return True
                else:
                    webhook_log.success = False
                    webhook_log.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                    db.commit()

                    # Retry if not max retries
                    if retry_count < self.max_retries:
                        return await self.send_webhook(
                            url, event_type, payload, organization_id, retry_count + 1
                        )

                    return False

        except httpx.TimeoutException as e:
            if webhook_log:
                webhook_log.success = False
                webhook_log.error_message = f"Timeout: {str(e)}"
                db.commit()

            # Retry on timeout
            if retry_count < self.max_retries:
                return await self.send_webhook(
                    url, event_type, payload, organization_id, retry_count + 1
                )

            return False

        except Exception as e:
            if webhook_log:
                webhook_log.success = False
                webhook_log.error_message = f"Error: {str(e)}"
                db.commit()

            return False

        finally:
            db.close()

    async def send_property_created_webhook(
        self,
        url: str,
        property_data: Dict[str, Any],
        organization_id: int,
    ) -> bool:
        """Send property.created webhook."""
        return await self.send_webhook(
            url,
            "property.created",
            property_data,
            organization_id,
        )

    async def send_lead_created_webhook(
        self,
        url: str,
        lead_data: Dict[str, Any],
        organization_id: int,
    ) -> bool:
        """Send lead.created webhook."""
        return await self.send_webhook(
            url,
            "lead.created",
            lead_data,
            organization_id,
        )

    async def send_deal_closed_webhook(
        self,
        url: str,
        deal_data: Dict[str, Any],
        organization_id: int,
    ) -> bool:
        """Send deal.closed webhook."""
        return await self.send_webhook(
            url,
            "deal.closed",
            deal_data,
            organization_id,
        )

    async def send_campaign_completed_webhook(
        self,
        url: str,
        campaign_data: Dict[str, Any],
        organization_id: int,
    ) -> bool:
        """Send campaign.completed webhook."""
        return await self.send_webhook(
            url,
            "campaign.completed",
            campaign_data,
            organization_id,
        )


# Singleton instance
webhook_service = WebhookService()
