"""
Mock External Service Integrations for Demo Mode

Provides realistic mock implementations of all external services:
- SendGrid (Email)
- Twilio (SMS/Voice)
- MinIO (Object Storage)
- WeasyPrint (PDF Generation)
- Data Providers (ATTOM, Regrid)

These mocks return deterministic fake data without requiring API keys.
"""
from .sendgrid_mock import send_email as mock_send_email
from .sendgrid_mock import send_templated_email as mock_send_templated_email
from .twilio_mock import send_sms as mock_send_sms
from .twilio_mock import make_call as mock_make_call
from .twilio_mock import get_call_transcript as mock_get_call_transcript
from .storage_mock import upload_file as mock_upload_file
from .storage_mock import get_file_url as mock_get_file_url
from .storage_mock import delete_file as mock_delete_file
from .pdf_mock import generate_property_memo as mock_generate_property_memo
from .pdf_mock import generate_offer_packet as mock_generate_offer_packet

__all__ = [
    "mock_send_email",
    "mock_send_templated_email",
    "mock_send_sms",
    "mock_make_call",
    "mock_get_call_transcript",
    "mock_upload_file",
    "mock_get_file_url",
    "mock_delete_file",
    "mock_generate_property_memo",
    "mock_generate_offer_packet",
]
