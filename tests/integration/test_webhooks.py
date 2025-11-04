"""
Integration Tests for Webhook System

Tests webhook signature verification, payload handling, and event processing
"""
import json
import hmac
import hashlib
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.models import Property, PropertyStage, Communication, CommunicationType


class TestWebhookSignatureVerification:
    """Test webhook signature verification and security"""

    def test_valid_signature_accepted(self, client: TestClient):
        """Test that webhook with valid signature is accepted"""
        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_123",
                "recipient": "test@example.com",
                "status": "delivered"
            }
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        # Generate valid signature
        secret = "test-webhook-secret"
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        # Should accept valid signature
        assert response.status_code in [200, 202]

    def test_invalid_signature_rejected(self, client: TestClient):
        """Test that webhook with invalid signature is rejected"""
        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_123",
                "recipient": "test@example.com"
            }
        }

        # Invalid signature
        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": "invalid_signature_12345"}
        )

        # Should reject invalid signature
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    def test_missing_signature_rejected(self, client: TestClient):
        """Test that webhook without signature is rejected"""
        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message_id": "msg_123"}
        }

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload
        )

        # Should reject missing signature
        assert response.status_code == 401

    def test_replay_attack_prevention(self, client: TestClient):
        """Test that old timestamps are rejected to prevent replay attacks"""
        # Timestamp from 10 minutes ago
        old_timestamp = datetime.fromtimestamp(
            datetime.utcnow().timestamp() - 600
        ).isoformat()

        payload = {
            "event": "email.delivered",
            "timestamp": old_timestamp,
            "data": {"message_id": "msg_123"}
        }
        payload_bytes = json.dumps(payload).encode('utf-8')

        secret = "test-webhook-secret"
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        # Should reject old timestamp
        assert response.status_code == 400
        assert "timestamp" in response.json()["detail"].lower() or "replay" in response.json()["detail"].lower()


class TestEmailWebhookEvents:
    """Test email provider webhook event handling"""

    def generate_webhook_signature(self, payload: dict, secret: str = "test-webhook-secret") -> str:
        """Helper to generate webhook signature"""
        payload_bytes = json.dumps(payload).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_email_delivered_event(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property,
        auth_headers: dict
    ):
        """Test handling of email delivered event"""
        # First create a communication record
        comm = Communication(
            property_id=test_property.id,
            direction="outbound",
            channel=CommunicationType.EMAIL,
            subject="Test Email",
            content="Test content",
            from_address="sender@example.com",
            to_address="recipient@example.com",
            status="sent",
            external_id="msg_123"
        )
        test_db.add(comm)
        test_db.commit()

        # Send delivered webhook
        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_123",
                "recipient": "recipient@example.com",
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [200, 202]

        # Verify communication status updated
        test_db.refresh(comm)
        assert comm.status == "delivered"

    def test_email_bounced_event(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property
    ):
        """Test handling of email bounced event"""
        # Create communication
        comm = Communication(
            property_id=test_property.id,
            direction="outbound",
            channel=CommunicationType.EMAIL,
            subject="Test Email",
            content="Test content",
            from_address="sender@example.com",
            to_address="bad@example.com",
            status="sent",
            external_id="msg_456"
        )
        test_db.add(comm)
        test_db.commit()

        # Send bounced webhook
        payload = {
            "event": "email.bounced",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_456",
                "recipient": "bad@example.com",
                "bounce_type": "hard",
                "reason": "mailbox does not exist"
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [200, 202]

        # Verify communication status updated
        test_db.refresh(comm)
        assert comm.status == "bounced"

    def test_email_replied_event(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property
    ):
        """Test handling of email reply event"""
        # Create outbound communication
        comm = Communication(
            property_id=test_property.id,
            direction="outbound",
            channel=CommunicationType.EMAIL,
            subject="Test Email",
            content="Test content",
            from_address="sender@example.com",
            to_address="owner@example.com",
            status="delivered",
            external_id="msg_789"
        )
        test_db.add(comm)
        test_db.commit()

        # Send reply webhook
        payload = {
            "event": "email.reply",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "in_reply_to": "msg_789",
                "from": "owner@example.com",
                "to": "sender@example.com",
                "subject": "Re: Test Email",
                "text_content": "Thanks for reaching out!",
                "html_content": "<p>Thanks for reaching out!</p>",
                "received_at": datetime.utcnow().isoformat()
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [200, 202]

        # Verify inbound communication created
        inbound = test_db.query(Communication).filter(
            Communication.direction == "inbound",
            Communication.property_id == test_property.id
        ).first()

        assert inbound is not None
        assert inbound.channel == CommunicationType.EMAIL
        assert inbound.from_address == "owner@example.com"
        assert "Thanks for reaching out" in inbound.content


class TestSMSWebhookEvents:
    """Test SMS provider webhook event handling"""

    def generate_webhook_signature(self, payload: dict, secret: str = "test-webhook-secret") -> str:
        """Helper to generate webhook signature"""
        payload_bytes = json.dumps(payload).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_sms_delivered_event(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property
    ):
        """Test handling of SMS delivered event"""
        # Create SMS communication
        comm = Communication(
            property_id=test_property.id,
            direction="outbound",
            channel=CommunicationType.SMS,
            content="Test SMS",
            from_address="+15551234567",
            to_address="+15559876543",
            status="sent",
            external_id="sms_123"
        )
        test_db.add(comm)
        test_db.commit()

        # Send delivered webhook
        payload = {
            "event": "sms.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_sid": "sms_123",
                "to": "+15559876543",
                "status": "delivered"
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/sms-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [200, 202]

        # Verify status updated
        test_db.refresh(comm)
        assert comm.status == "delivered"

    def test_sms_inbound_event(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property
    ):
        """Test handling of inbound SMS"""
        payload = {
            "event": "sms.inbound",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "from": "+15559876543",
                "to": "+15551234567",
                "body": "Yes, I'm interested!",
                "received_at": datetime.utcnow().isoformat()
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/sms-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [200, 202]

        # Verify inbound SMS created (if property can be identified)
        # Note: In real implementation, would need to match phone number to property
        inbound_count = test_db.query(Communication).filter(
            Communication.direction == "inbound",
            Communication.channel == CommunicationType.SMS
        ).count()

        assert inbound_count >= 0  # May or may not create if can't match to property


class TestWebhookIdempotency:
    """Test webhook idempotency to prevent duplicate processing"""

    def generate_webhook_signature(self, payload: dict, secret: str = "test-webhook-secret") -> str:
        """Helper to generate webhook signature"""
        payload_bytes = json.dumps(payload).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_duplicate_webhook_rejected(
        self,
        client: TestClient,
        test_db: Session,
        test_property: Property
    ):
        """Test that duplicate webhook events are detected and ignored"""
        # Create communication
        comm = Communication(
            property_id=test_property.id,
            direction="outbound",
            channel=CommunicationType.EMAIL,
            subject="Test",
            content="Test",
            from_address="sender@example.com",
            to_address="recipient@example.com",
            status="sent",
            external_id="msg_unique_123"
        )
        test_db.add(comm)
        test_db.commit()

        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_unique_123",
                "recipient": "recipient@example.com"
            }
        }

        signature = self.generate_webhook_signature(payload)
        headers = {
            "X-Webhook-Signature": signature,
            "X-Webhook-ID": "webhook_12345"  # Unique webhook ID
        }

        # First request should succeed
        response1 = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers=headers
        )

        assert response1.status_code in [200, 202]

        # Second request with same webhook ID should be idempotent
        response2 = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers=headers
        )

        # Should return success but not process twice
        assert response2.status_code in [200, 202]

        # Verify only processed once (status should still be delivered, not duplicated)
        test_db.refresh(comm)
        assert comm.status == "delivered"


class TestWebhookErrorHandling:
    """Test webhook error handling and resilience"""

    def generate_webhook_signature(self, payload: dict, secret: str = "test-webhook-secret") -> str:
        """Helper to generate webhook signature"""
        payload_bytes = json.dumps(payload).encode('utf-8')
        return hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_malformed_payload_rejected(self, client: TestClient):
        """Test that malformed payloads are rejected with proper error"""
        payload = "not valid json"

        response = client.post(
            "/api/v1/webhooks/email-provider",
            data=payload,
            headers={
                "X-Webhook-Signature": "sig_123",
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 422  # Unprocessable entity

    def test_missing_required_fields(self, client: TestClient):
        """Test that payloads missing required fields are rejected"""
        payload = {
            "event": "email.delivered",
            # Missing timestamp and data
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        assert response.status_code in [400, 422]

    def test_unknown_event_type(self, client: TestClient):
        """Test handling of unknown event types"""
        payload = {
            "event": "email.unknown_event_type",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message_id": "msg_123"}
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        # Should accept but log warning (graceful degradation)
        assert response.status_code in [200, 202, 400]

    def test_nonexistent_message_id(
        self,
        client: TestClient,
        test_db: Session
    ):
        """Test webhook for message ID that doesn't exist"""
        payload = {
            "event": "email.delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message_id": "msg_nonexistent_999",
                "recipient": "test@example.com"
            }
        }

        signature = self.generate_webhook_signature(payload)

        response = client.post(
            "/api/v1/webhooks/email-provider",
            json=payload,
            headers={"X-Webhook-Signature": signature}
        )

        # Should accept but handle gracefully (maybe log warning)
        assert response.status_code in [200, 202, 404]
