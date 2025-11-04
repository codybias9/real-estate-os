"""
SMS Provider Implementations

MockSmsProvider: Posts to Mock Twilio service for development
TwilioProvider: Real Twilio API for production
"""
import logging
import requests
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from api.config import get_config

logger = logging.getLogger(__name__)


class SmsProvider(ABC):
    """Abstract SMS provider interface"""

    @abstractmethod
    def send_sms(self, to: str, body: str, from_phone: Optional[str] = None) -> Dict:
        """Send SMS and return result"""
        pass


class MockSmsProvider(SmsProvider):
    """
    Mock SMS provider using Mock Twilio service

    Posts to http://mock-twilio:4010/Messages.json
    Writes artifacts to audit_artifacts/sent_sms/
    """

    def __init__(self):
        self.config = get_config()
        self.mock_twilio_url = self.config.MOCK_TWILIO_URL
        self.from_phone = self.config.TWILIO_FROM_PHONE
        self.artifacts_dir = Path(self.config.AUDIT_ARTIFACTS_DIR) / "sent_sms"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MockSmsProvider initialized: {self.mock_twilio_url}")

    def send_sms(self, to: str, body: str, from_phone: Optional[str] = None) -> Dict:
        """
        Send SMS via Mock Twilio service

        Args:
            to: Phone number in E.164 format (e.g., +15551234567)
            body: SMS body text (max 160 chars for single message)
            from_phone: Optional sender phone, defaults to config

        Returns:
            Dict with message_id, status, sid, provider
        """
        from_phone = from_phone or self.from_phone
        timestamp = datetime.utcnow()

        # Generate mock SID (Twilio format: SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
        import uuid
        mock_sid = f"SM{uuid.uuid4().hex}"

        # Prepare request payload (Twilio format)
        payload = {
            "To": to,
            "From": from_phone,
            "Body": body
        }

        try:
            # Post to Mock Twilio service
            response = requests.post(
                f"{self.mock_twilio_url}/Messages.json",
                data=payload,
                timeout=5
            )

            if response.status_code in [200, 201]:
                result = response.json()
                message_id = result.get("sid", mock_sid)
                logger.info(f"SMS sent via Mock Twilio: {to[:8]}*** -> SID {message_id}")
            else:
                logger.warning(f"Mock Twilio returned {response.status_code}: {response.text}")
                message_id = mock_sid
                result = {
                    "sid": mock_sid,
                    "status": "queued",
                    "error_code": None,
                    "error_message": None
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Mock Twilio request failed: {e}")
            # Still return success for development
            message_id = mock_sid
            result = {
                "sid": mock_sid,
                "status": "queued",
                "error_code": None,
                "error_message": str(e)
            }

        # Record to artifacts
        artifact = {
            "timestamp": timestamp.isoformat(),
            "to": to,
            "from": from_phone,
            "body": body,
            "sid": message_id,
            "provider": "mock_twilio",
            "status": result.get("status", "queued")
        }

        artifact_file = self.artifacts_dir / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{to.replace('+', '').replace(' ', '_')}.json"
        with open(artifact_file, 'w') as f:
            json.dump(artifact, f, indent=2)

        return {
            "message_id": message_id,
            "sid": message_id,
            "status": result.get("status", "queued"),
            "provider": "mock_twilio",
            "to": to,
            "from": from_phone
        }


class TwilioProvider(SmsProvider):
    """
    Real Twilio SMS provider for production

    Requires TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in configuration
    """

    def __init__(self):
        self.config = get_config()
        self.account_sid = self.config.TWILIO_ACCOUNT_SID
        self.auth_token = self.config.TWILIO_AUTH_TOKEN
        self.from_phone = self.config.TWILIO_FROM_PHONE

        if not self.account_sid or not self.auth_token:
            logger.warning("TwilioProvider initialized without credentials")
        else:
            logger.info(f"TwilioProvider initialized: {self.account_sid[:8]}***")

    def send_sms(self, to: str, body: str, from_phone: Optional[str] = None) -> Dict:
        """
        Send SMS via Twilio API

        Args:
            to: Phone number in E.164 format
            body: SMS body text
            from_phone: Optional sender phone

        Returns:
            Dict with message_id, status, sid, provider
        """
        from_phone = from_phone or self.from_phone

        if not self.account_sid or not self.auth_token:
            logger.error("Twilio credentials not configured")
            return {
                "message_id": None,
                "sid": None,
                "status": "failed",
                "error": "Twilio credentials not configured",
                "provider": "twilio"
            }

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)

            message = client.messages.create(
                to=to,
                from_=from_phone,
                body=body
            )

            logger.info(f"SMS sent via Twilio: {to[:8]}*** -> SID {message.sid}")

            return {
                "message_id": message.sid,
                "sid": message.sid,
                "status": message.status,
                "provider": "twilio",
                "to": message.to,
                "from": message.from_
            }

        except Exception as e:
            logger.error(f"Twilio send failed: {e}")
            return {
                "message_id": None,
                "sid": None,
                "status": "failed",
                "error": str(e),
                "provider": "twilio"
            }
