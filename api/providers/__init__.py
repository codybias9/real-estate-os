"""
Provider Registry & Dependency Injection

Manages provider implementations based on APP_MODE and feature flags.
Enables swapping between mock and production providers without code changes.
"""
from typing import Optional
from api.config import get_config, is_mock_mode

# Lazy imports to avoid circular dependencies
_email_provider = None
_sms_provider = None
_storage_provider = None
_pdf_provider = None
_llm_provider = None


def get_email_provider():
    """Get email provider based on configuration"""
    global _email_provider

    if _email_provider is None:
        if is_mock_mode():
            from api.providers.email import MockEmailProvider
            _email_provider = MockEmailProvider()
        else:
            from api.providers.email import SendGridProvider
            _email_provider = SendGridProvider()

    return _email_provider


def get_sms_provider():
    """Get SMS provider based on configuration"""
    global _sms_provider

    if _sms_provider is None:
        if is_mock_mode():
            from api.providers.sms import MockSmsProvider
            _sms_provider = MockSmsProvider()
        else:
            from api.providers.sms import TwilioProvider
            _sms_provider = TwilioProvider()

    return _sms_provider


def get_storage_provider():
    """Get storage provider based on configuration"""
    global _storage_provider

    if _storage_provider is None:
        if is_mock_mode():
            from api.providers.storage import MinIOProvider
            _storage_provider = MinIOProvider()
        else:
            from api.providers.storage import S3Provider
            _storage_provider = S3Provider()

    return _storage_provider


def get_pdf_provider():
    """Get PDF provider based on configuration"""
    global _pdf_provider

    if _pdf_provider is None:
        if is_mock_mode():
            from api.providers.pdf import GotenbergProvider
            _pdf_provider = GotenbergProvider()
        else:
            from api.providers.pdf import WeasyPrintProvider
            _pdf_provider = WeasyPrintProvider()

    return _pdf_provider


def get_llm_provider():
    """Get LLM provider based on configuration"""
    global _llm_provider

    if _llm_provider is None:
        config = get_config()
        if is_mock_mode() or not config.FEATURE_USE_LLM:
            from api.providers.llm import DeterministicTemplateProvider
            _llm_provider = DeterministicTemplateProvider()
        else:
            from api.providers.llm import OpenAIProvider
            _llm_provider = OpenAIProvider()

    return _llm_provider


def reset_providers():
    """Reset all providers (useful for testing)"""
    global _email_provider, _sms_provider, _storage_provider, _pdf_provider, _llm_provider
    _email_provider = None
    _sms_provider = None
    _storage_provider = None
    _pdf_provider = None
    _llm_provider = None
