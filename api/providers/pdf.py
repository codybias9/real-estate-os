"""
PDF Provider Implementations

GotenbergProvider: Local Gotenberg service for development
WeasyPrintProvider: Python-based PDF generation for production
"""
import logging
import requests
import io
from abc import ABC, abstractmethod
from typing import Dict, Optional, BinaryIO
from pathlib import Path

from api.config import get_config

logger = logging.getLogger(__name__)


class PdfProvider(ABC):
    """Abstract PDF provider interface"""

    @abstractmethod
    def generate_pdf_from_html(self, html: str, filename: str) -> bytes:
        """Generate PDF from HTML string"""
        pass

    @abstractmethod
    def generate_pdf_from_url(self, url: str, filename: str) -> bytes:
        """Generate PDF from URL"""
        pass


class GotenbergProvider(PdfProvider):
    """
    Gotenberg PDF provider for local development

    Connects to Gotenberg at http://gotenberg:3000
    Fast, deterministic PDF generation using Chromium
    """

    def __init__(self):
        self.config = get_config()
        self.gotenberg_url = self.config.GOTENBERG_URL
        logger.info(f"GotenbergProvider initialized: {self.gotenberg_url}")

    def generate_pdf_from_html(self, html: str, filename: str) -> bytes:
        """
        Generate PDF from HTML string using Gotenberg

        Args:
            html: HTML content string
            filename: Output filename (for logging)

        Returns:
            PDF content as bytes
        """
        try:
            # Gotenberg expects files in multipart/form-data
            files = {
                'index.html': ('index.html', html.encode('utf-8'), 'text/html')
            }

            response = requests.post(
                f"{self.gotenberg_url}/forms/chromium/convert/html",
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"PDF generated via Gotenberg: {filename} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"Gotenberg returned {response.status_code}: {response.text}")
                raise Exception(f"Gotenberg PDF generation failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Gotenberg request failed: {e}")
            raise Exception(f"Failed to connect to Gotenberg: {e}")

    def generate_pdf_from_url(self, url: str, filename: str) -> bytes:
        """
        Generate PDF from URL using Gotenberg

        Args:
            url: URL to convert to PDF
            filename: Output filename (for logging)

        Returns:
            PDF content as bytes
        """
        try:
            data = {
                'url': url
            }

            response = requests.post(
                f"{self.gotenberg_url}/forms/chromium/convert/url",
                data=data,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"PDF generated from URL via Gotenberg: {filename} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"Gotenberg returned {response.status_code}: {response.text}")
                raise Exception(f"Gotenberg PDF generation failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Gotenberg request failed: {e}")
            raise Exception(f"Failed to connect to Gotenberg: {e}")


class WeasyPrintProvider(PdfProvider):
    """
    WeasyPrint PDF provider for production

    Pure Python PDF generation - no external dependencies
    Good for simple documents, slower than Chromium-based options
    """

    def __init__(self):
        self.config = get_config()
        logger.info("WeasyPrintProvider initialized")

    def generate_pdf_from_html(self, html: str, filename: str) -> bytes:
        """
        Generate PDF from HTML string using WeasyPrint

        Args:
            html: HTML content string
            filename: Output filename (for logging)

        Returns:
            PDF content as bytes
        """
        try:
            from weasyprint import HTML, CSS
            from io import BytesIO

            # Generate PDF
            pdf_buffer = BytesIO()
            HTML(string=html).write_pdf(pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()

            logger.info(f"PDF generated via WeasyPrint: {filename} ({len(pdf_bytes)} bytes)")
            return pdf_bytes

        except ImportError:
            logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
            raise Exception("WeasyPrint not available - install with 'pip install weasyprint'")

        except Exception as e:
            logger.error(f"WeasyPrint generation failed: {e}")
            raise Exception(f"PDF generation failed: {e}")

    def generate_pdf_from_url(self, url: str, filename: str) -> bytes:
        """
        Generate PDF from URL using WeasyPrint

        Args:
            url: URL to convert to PDF
            filename: Output filename (for logging)

        Returns:
            PDF content as bytes
        """
        try:
            from weasyprint import HTML
            from io import BytesIO

            # Fetch URL and generate PDF
            pdf_buffer = BytesIO()
            HTML(url=url).write_pdf(pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()

            logger.info(f"PDF generated from URL via WeasyPrint: {filename} ({len(pdf_bytes)} bytes)")
            return pdf_bytes

        except ImportError:
            logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
            raise Exception("WeasyPrint not available - install with 'pip install weasyprint'")

        except Exception as e:
            logger.error(f"WeasyPrint URL conversion failed: {e}")
            raise Exception(f"PDF generation from URL failed: {e}")


class DocRaptorProvider(PdfProvider):
    """
    DocRaptor PDF provider (cloud service)

    High-quality PDF generation with Prince XML engine
    Paid service - requires API key
    """

    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.DOCRAPTOR_API_KEY

        if not self.api_key:
            logger.warning("DocRaptorProvider initialized without API key")
        else:
            logger.info("DocRaptorProvider initialized")

    def generate_pdf_from_html(self, html: str, filename: str) -> bytes:
        """
        Generate PDF from HTML using DocRaptor

        Args:
            html: HTML content string
            filename: Output filename

        Returns:
            PDF content as bytes
        """
        if not self.api_key:
            logger.error("DocRaptor API key not configured")
            raise Exception("DocRaptor API key not configured")

        try:
            import docraptor

            doc_api = docraptor.DocApi()
            doc_api.api_client.configuration.username = self.api_key

            create_response = doc_api.create_doc({
                "test": False,  # Set to True for test mode
                "document_type": "pdf",
                "document_content": html,
                "name": filename,
                "prince_options": {
                    "media": "print",
                    "baseurl": "https://realestateos.com"
                }
            })

            logger.info(f"PDF generated via DocRaptor: {filename} ({len(create_response)} bytes)")
            return create_response

        except ImportError:
            logger.error("DocRaptor client not installed. Install with: pip install docraptor")
            raise Exception("DocRaptor not available - install with 'pip install docraptor'")

        except Exception as e:
            logger.error(f"DocRaptor generation failed: {e}")
            raise Exception(f"PDF generation failed: {e}")

    def generate_pdf_from_url(self, url: str, filename: str) -> bytes:
        """
        Generate PDF from URL using DocRaptor

        Args:
            url: URL to convert
            filename: Output filename

        Returns:
            PDF content as bytes
        """
        if not self.api_key:
            logger.error("DocRaptor API key not configured")
            raise Exception("DocRaptor API key not configured")

        try:
            import docraptor

            doc_api = docraptor.DocApi()
            doc_api.api_client.configuration.username = self.api_key

            create_response = doc_api.create_doc({
                "test": False,
                "document_type": "pdf",
                "document_url": url,
                "name": filename
            })

            logger.info(f"PDF generated from URL via DocRaptor: {filename} ({len(create_response)} bytes)")
            return create_response

        except ImportError:
            logger.error("DocRaptor client not installed. Install with: pip install docraptor")
            raise Exception("DocRaptor not available - install with 'pip install docraptor'")

        except Exception as e:
            logger.error(f"DocRaptor URL conversion failed: {e}")
            raise Exception(f"PDF generation from URL failed: {e}")
