"""PDF generation from HTML

Converts HTML to high-quality PDFs using WeasyPrint.
"""
import logging
import io
from typing import Optional
from pathlib import Path
import tempfile

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generates PDFs from HTML

    Uses WeasyPrint for high-quality PDF rendering with CSS support.
    """

    def __init__(self):
        """Initialize PDF generator"""
        self.font_config = FontConfiguration()
        logger.info("PDFGenerator initialized")

    def html_to_pdf(
        self,
        html: str,
        output_path: Optional[str] = None,
        custom_css: Optional[str] = None
    ) -> bytes:
        """
        Convert HTML to PDF

        Args:
            html: HTML string to convert
            output_path: Optional path to save PDF (if None, returns bytes)
            custom_css: Optional custom CSS to apply

        Returns:
            PDF as bytes
        """
        logger.info("Converting HTML to PDF")

        try:
            # Create HTML object from string
            html_obj = HTML(string=html)

            # Prepare CSS
            css_list = []
            if custom_css:
                css_list.append(CSS(string=custom_css, font_config=self.font_config))

            # Add default PDF optimizations
            default_css = """
                @page {
                    size: A4;
                    margin: 0;
                }
                body {
                    margin: 0;
                    padding: 0;
                }
                /* Ensure images fit */
                img {
                    max-width: 100%;
                    height: auto;
                }
                /* Print-friendly styles */
                @media print {
                    .no-print {
                        display: none;
                    }
                }
            """
            css_list.append(CSS(string=default_css, font_config=self.font_config))

            # Render PDF
            if output_path:
                # Write to file
                html_obj.write_pdf(
                    output_path,
                    stylesheets=css_list,
                    font_config=self.font_config
                )
                logger.info(f"PDF saved to: {output_path}")

                # Read back for return
                with open(output_path, 'rb') as f:
                    pdf_bytes = f.read()
            else:
                # Render to bytes
                pdf_bytes = html_obj.write_pdf(
                    stylesheets=css_list,
                    font_config=self.font_config
                )

            logger.info(f"PDF generated successfully ({len(pdf_bytes)} bytes)")

            return pdf_bytes

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation failed: {e}")

    def html_file_to_pdf(self, html_path: str, output_path: str) -> bytes:
        """
        Convert HTML file to PDF

        Args:
            html_path: Path to HTML file
            output_path: Path to save PDF

        Returns:
            PDF as bytes
        """
        logger.info(f"Converting HTML file to PDF: {html_path}")

        if not Path(html_path).exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()

        return self.html_to_pdf(html, output_path)

    @staticmethod
    def validate_pdf(pdf_bytes: bytes) -> bool:
        """
        Validate PDF file

        Args:
            pdf_bytes: PDF content as bytes

        Returns:
            True if valid PDF
        """
        # Check PDF magic number (PDF files start with %PDF-)
        if not pdf_bytes.startswith(b'%PDF-'):
            logger.error("Invalid PDF: Missing PDF header")
            return False

        # Check minimum size (valid PDFs are at least a few hundred bytes)
        if len(pdf_bytes) < 100:
            logger.error(f"Invalid PDF: File too small ({len(pdf_bytes)} bytes)")
            return False

        logger.info("PDF validation successful")
        return True

    def html_to_pdf_with_images(
        self,
        html: str,
        images: dict = None,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Convert HTML to PDF with embedded images

        Args:
            html: HTML string
            images: Dictionary of image_name -> image_bytes
            output_path: Optional path to save PDF

        Returns:
            PDF as bytes
        """
        logger.info("Converting HTML with images to PDF")

        # If images provided, we need to embed them as base64 data URIs
        # or save them to temp files and reference them

        if images:
            # Create temp directory for images
            import base64
            from urllib.parse import quote

            # Replace image references with base64 data URIs
            for img_name, img_bytes in images.items():
                # Determine MIME type from extension
                ext = Path(img_name).suffix.lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = mime_types.get(ext, 'image/jpeg')

                # Encode to base64
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                data_uri = f"data:{mime_type};base64,{img_b64}"

                # Replace in HTML
                html = html.replace(f'src="{img_name}"', f'src="{data_uri}"')
                html = html.replace(f"src='{img_name}'", f"src='{data_uri}'")

        return self.html_to_pdf(html, output_path)
