"""
Integration Provider Factory

Switches between real and mock implementations based on MOCK_MODE environment variable.

Usage:
    from api.integrations.factory import get_email_client, get_sms_client

    # Will return mock or real client based on MOCK_MODE
    send_email = get_email_client().send_email
    send_sms = get_sms_client().send_sms

Environment Variables:
    MOCK_MODE=true    - Use mock implementations (no external API calls)
    MOCK_MODE=false   - Use real implementations (requires API keys)
"""
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

def is_mock_mode() -> bool:
    """
    Check if application is running in mock mode

    Returns:
        True if MOCK_MODE=true, False otherwise
    """
    mock_mode = os.getenv("MOCK_MODE", "false").lower()
    return mock_mode in ("true", "1", "yes", "on")


# ============================================================================
# EMAIL CLIENT (SendGrid)
# ============================================================================

class EmailClient:
    """Email client wrapper"""

    def __init__(self):
        if is_mock_mode():
            logger.info("[FACTORY] Using MOCK email client (SendGrid)")
            from api.integrations.mock import sendgrid_mock
            self._impl = sendgrid_mock
        else:
            logger.info("[FACTORY] Using REAL email client (SendGrid)")
            from api.integrations import sendgrid_client
            self._impl = sendgrid_client

    def send_email(self, *args, **kwargs):
        """Send email (delegates to real or mock implementation)"""
        return self._impl.send_email(*args, **kwargs)

    def send_templated_email(self, *args, **kwargs):
        """Send templated email (delegates to real or mock implementation)"""
        return self._impl.send_templated_email(*args, **kwargs)


def get_email_client() -> EmailClient:
    """Get email client (mock or real based on MOCK_MODE)"""
    return EmailClient()


# ============================================================================
# SMS/VOICE CLIENT (Twilio)
# ============================================================================

class SMSClient:
    """SMS/Voice client wrapper"""

    def __init__(self):
        if is_mock_mode():
            logger.info("[FACTORY] Using MOCK SMS/voice client (Twilio)")
            from api.integrations.mock import twilio_mock
            self._impl = twilio_mock
        else:
            logger.info("[FACTORY] Using REAL SMS/voice client (Twilio)")
            from api.integrations import twilio_client
            self._impl = twilio_client

    def send_sms(self, *args, **kwargs):
        """Send SMS (delegates to real or mock implementation)"""
        return self._impl.send_sms(*args, **kwargs)

    def make_call(self, *args, **kwargs):
        """Make voice call (delegates to real or mock implementation)"""
        return self._impl.make_call(*args, **kwargs)

    def get_call_transcript(self, *args, **kwargs):
        """Get call transcription (delegates to real or mock implementation)"""
        return self._impl.get_call_transcript(*args, **kwargs)


def get_sms_client() -> SMSClient:
    """Get SMS/voice client (mock or real based on MOCK_MODE)"""
    return SMSClient()


# ============================================================================
# STORAGE CLIENT (MinIO/S3)
# ============================================================================

class StorageClient:
    """Object storage client wrapper"""

    def __init__(self):
        if is_mock_mode():
            logger.info("[FACTORY] Using MOCK storage client (MinIO)")
            from api.integrations.mock import storage_mock
            self._impl = storage_mock
        else:
            logger.info("[FACTORY] Using REAL storage client (MinIO)")
            from api.integrations import storage_client
            self._impl = storage_client

    def upload_file(self, *args, **kwargs):
        """Upload file (delegates to real or mock implementation)"""
        return self._impl.upload_file(*args, **kwargs)

    def get_file_url(self, *args, **kwargs):
        """Get file URL (delegates to real or mock implementation)"""
        return self._impl.get_file_url(*args, **kwargs)

    def delete_file(self, *args, **kwargs):
        """Delete file (delegates to real or mock implementation)"""
        return self._impl.delete_file(*args, **kwargs)


def get_storage_client() -> StorageClient:
    """Get storage client (mock or real based on MOCK_MODE)"""
    return StorageClient()


# ============================================================================
# PDF GENERATOR (WeasyPrint)
# ============================================================================

class PDFGenerator:
    """PDF generation client wrapper"""

    def __init__(self):
        if is_mock_mode():
            logger.info("[FACTORY] Using MOCK PDF generator")
            from api.integrations.mock import pdf_mock
            self._impl = pdf_mock
        else:
            logger.info("[FACTORY] Using REAL PDF generator (WeasyPrint)")
            from api.integrations import pdf_generator
            self._impl = pdf_generator

    def generate_property_memo(self, *args, **kwargs):
        """Generate property memo PDF (delegates to real or mock implementation)"""
        return self._impl.generate_property_memo(*args, **kwargs)

    def generate_offer_packet(self, *args, **kwargs):
        """Generate offer packet PDF (delegates to real or mock implementation)"""
        return self._impl.generate_offer_packet(*args, **kwargs)


def get_pdf_generator() -> PDFGenerator:
    """Get PDF generator (mock or real based on MOCK_MODE)"""
    return PDFGenerator()


# ============================================================================
# CONVENIENCE FUNCTIONS (Backwards Compatibility)
# ============================================================================

# Email
def send_email(*args, **kwargs):
    """Send email using appropriate client"""
    return get_email_client().send_email(*args, **kwargs)


def send_templated_email(*args, **kwargs):
    """Send templated email using appropriate client"""
    return get_email_client().send_templated_email(*args, **kwargs)


# SMS/Voice
def send_sms(*args, **kwargs):
    """Send SMS using appropriate client"""
    return get_sms_client().send_sms(*args, **kwargs)


def make_call(*args, **kwargs):
    """Make call using appropriate client"""
    return get_sms_client().make_call(*args, **kwargs)


def get_call_transcript(*args, **kwargs):
    """Get call transcript using appropriate client"""
    return get_sms_client().get_call_transcript(*args, **kwargs)


# Storage
def upload_file(*args, **kwargs):
    """Upload file using appropriate client"""
    return get_storage_client().upload_file(*args, **kwargs)


def get_file_url(*args, **kwargs):
    """Get file URL using appropriate client"""
    return get_storage_client().get_file_url(*args, **kwargs)


def delete_file(*args, **kwargs):
    """Delete file using appropriate client"""
    return get_storage_client().delete_file(*args, **kwargs)


# PDF Generation
def generate_property_memo(*args, **kwargs):
    """Generate property memo using appropriate generator"""
    return get_pdf_generator().generate_property_memo(*args, **kwargs)


def generate_offer_packet(*args, **kwargs):
    """Generate offer packet using appropriate generator"""
    return get_pdf_generator().generate_offer_packet(*args, **kwargs)


# ============================================================================
# INITIALIZATION LOGGING
# ============================================================================

def log_provider_status():
    """Log which providers are being used (mock or real)"""
    mode = "MOCK" if is_mock_mode() else "REAL"

    logger.info("=" * 70)
    logger.info(f"INTEGRATION PROVIDER MODE: {mode}")
    logger.info("=" * 70)
    logger.info(f"  Email (SendGrid):     {mode}")
    logger.info(f"  SMS/Voice (Twilio):   {mode}")
    logger.info(f"  Storage (MinIO):      {mode}")
    logger.info(f"  PDF (WeasyPrint):     {mode}")
    logger.info("=" * 70)

    if is_mock_mode():
        logger.info("⚠️  Running in MOCK MODE - No external API calls will be made")
        logger.info("   Perfect for demos, testing, and development")
        logger.info("   Set MOCK_MODE=false to use real external services")
    else:
        logger.info("✅ Running in REAL MODE - External API calls enabled")
        logger.info("   Ensure all API keys are configured in environment")


# Log on import
log_provider_status()
