"""
Provider Factory

Central factory for instantiating providers based on APP_MODE.
Provides clean dependency injection for email, SMS, PDF, storage, and LLM providers.

Usage:
    from api.providers.factory import ProviderFactory

    factory = ProviderFactory()
    email_provider = factory.get_email_provider()
    email_provider.send_email(to="user@example.com", subject="Hello", body="World")

Configuration:
    APP_MODE=mock (default): Uses MailHog, Mock Twilio, MinIO, Gotenberg, etc.
    APP_MODE=production: Uses SendGrid, Twilio, S3, WeasyPrint, OpenAI, etc.

    Individual providers can be overridden with environment variables:
    PROVIDER_MODE_EMAIL=mock|real
    PROVIDER_MODE_SMS=mock|real
    PROVIDER_MODE_STORAGE=mock|real
    PROVIDER_MODE_PDF=mock|real
    PROVIDER_MODE_LLM=mock|real
"""
import logging
import os
from typing import Optional

from api.config import get_config, is_mock_mode

logger = logging.getLogger(__name__)


class ProviderMode:
    """Provider mode constants"""
    MOCK = "mock"
    REAL = "real"


class ProviderFactory:
    """
    Central factory for provider instantiation.

    Manages provider lifecycle and caching.
    """

    def __init__(self):
        self.config = get_config()
        self._email_provider = None
        self._sms_provider = None
        self._storage_provider = None
        self._pdf_provider = None
        self._llm_provider = None

        # Log provider mode on initialization
        mode = "MOCK" if is_mock_mode() else "PRODUCTION"
        logger.info(f"ProviderFactory initialized in {mode} mode")

    def _get_provider_mode(self, provider_type: str) -> str:
        """
        Determine provider mode for a specific provider type.

        Checks env var PROVIDER_MODE_{TYPE} first, then falls back to APP_MODE.

        Args:
            provider_type: email, sms, storage, pdf, llm

        Returns:
            'mock' or 'real'
        """
        # Check for provider-specific override
        env_key = f"PROVIDER_MODE_{provider_type.upper()}"
        mode = os.getenv(env_key)

        if mode:
            logger.debug(f"Using {env_key}={mode} for {provider_type} provider")
            return mode.lower()

        # Fall back to APP_MODE
        if is_mock_mode():
            return ProviderMode.MOCK
        else:
            return ProviderMode.REAL

    def get_email_provider(self):
        """Get email provider based on configuration"""
        if self._email_provider is None:
            mode = self._get_provider_mode("email")

            if mode == ProviderMode.MOCK:
                from api.providers.email import MockEmailProvider
                self._email_provider = MockEmailProvider()
                logger.info("Using MockEmailProvider (MailHog)")
            else:
                from api.providers.email import SendGridProvider
                self._email_provider = SendGridProvider()
                logger.info("Using SendGridProvider")

        return self._email_provider

    def get_sms_provider(self):
        """Get SMS provider based on configuration"""
        if self._sms_provider is None:
            mode = self._get_provider_mode("sms")

            if mode == ProviderMode.MOCK:
                from api.providers.sms import MockSmsProvider
                self._sms_provider = MockSmsProvider()
                logger.info("Using MockSmsProvider")
            else:
                from api.providers.sms import TwilioProvider
                self._sms_provider = TwilioProvider()
                logger.info("Using TwilioProvider")

        return self._sms_provider

    def get_storage_provider(self):
        """Get storage provider based on configuration"""
        if self._storage_provider is None:
            mode = self._get_provider_mode("storage")

            if mode == ProviderMode.MOCK:
                from api.providers.storage import MinIOProvider
                self._storage_provider = MinIOProvider()
                logger.info("Using MinIOProvider (local storage)")
            else:
                from api.providers.storage import S3Provider
                self._storage_provider = S3Provider()
                logger.info("Using S3Provider (AWS S3)")

        return self._storage_provider

    def get_pdf_provider(self):
        """Get PDF provider based on configuration"""
        if self._pdf_provider is None:
            mode = self._get_provider_mode("pdf")

            if mode == ProviderMode.MOCK:
                from api.providers.pdf import GotenbergProvider
                self._pdf_provider = GotenbergProvider()
                logger.info("Using GotenbergProvider (Gotenberg container)")
            else:
                from api.providers.pdf import WeasyPrintProvider
                self._pdf_provider = WeasyPrintProvider()
                logger.info("Using WeasyPrintProvider")

        return self._pdf_provider

    def get_llm_provider(self):
        """Get LLM provider based on configuration"""
        if self._llm_provider is None:
            mode = self._get_provider_mode("llm")

            # Also respect FEATURE_USE_LLM flag
            if mode == ProviderMode.MOCK or not self.config.FEATURE_USE_LLM:
                from api.providers.llm import DeterministicTemplateProvider
                self._llm_provider = DeterministicTemplateProvider()
                logger.info("Using DeterministicTemplateProvider (no LLM calls)")
            else:
                from api.providers.llm import OpenAIProvider
                self._llm_provider = OpenAIProvider()
                logger.info("Using OpenAIProvider (real LLM)")

        return self._llm_provider

    def reset_providers(self):
        """Reset all cached providers (useful for testing)"""
        self._email_provider = None
        self._sms_provider = None
        self._storage_provider = None
        self._pdf_provider = None
        self._llm_provider = None
        logger.info("All providers reset")

    def get_provider_status(self) -> dict:
        """
        Get status of all providers.

        Returns:
            Dict with provider names and their current mode/status
        """
        return {
            "app_mode": str(self.config.APP_MODE),
            "providers": {
                "email": self._get_provider_mode("email"),
                "sms": self._get_provider_mode("sms"),
                "storage": self._get_provider_mode("storage"),
                "pdf": self._get_provider_mode("pdf"),
                "llm": self._get_provider_mode("llm"),
            },
            "feature_flags": {
                "external_sends": self.config.FEATURE_EXTERNAL_SENDS,
                "use_llm": self.config.FEATURE_USE_LLM,
                "rate_limit": self.config.FEATURE_RATE_LIMIT,
                "webhook_signatures": self.config.FEATURE_WEBHOOK_SIGNATURES,
                "cache_responses": self.config.FEATURE_CACHE_RESPONSES,
            }
        }


# Global factory instance (singleton pattern)
_factory_instance: Optional[ProviderFactory] = None


def get_provider_factory() -> ProviderFactory:
    """
    Get the global provider factory instance.

    Returns:
        Singleton ProviderFactory instance
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = ProviderFactory()

    return _factory_instance


def reset_factory():
    """Reset the global factory instance (useful for testing)"""
    global _factory_instance
    if _factory_instance:
        _factory_instance.reset_providers()
    _factory_instance = None


# Convenience functions for direct provider access
def get_email_provider():
    """Convenience function to get email provider"""
    return get_provider_factory().get_email_provider()


def get_sms_provider():
    """Convenience function to get SMS provider"""
    return get_provider_factory().get_sms_provider()


def get_storage_provider():
    """Convenience function to get storage provider"""
    return get_provider_factory().get_storage_provider()


def get_pdf_provider():
    """Convenience function to get PDF provider"""
    return get_provider_factory().get_pdf_provider()


def get_llm_provider():
    """Convenience function to get LLM provider"""
    return get_provider_factory().get_llm_provider()


def get_provider_status() -> dict:
    """Convenience function to get provider status"""
    return get_provider_factory().get_provider_status()
