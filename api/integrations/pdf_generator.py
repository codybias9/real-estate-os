"""
PDF Generation using WeasyPrint
Generate property investment memos and offer packets
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO
import logging

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint not installed - PDF generation will fail")

logger = logging.getLogger(__name__)

# ============================================================================
# PDF GENERATION
# ============================================================================

def generate_property_memo(property_data: Dict[str, Any], template: str = "default") -> bytes:
    """
    Generate a property investment memo PDF

    Args:
        property_data: Property information including:
            - address, city, state, zip_code
            - beds, baths, sqft, year_built
            - assessed_value, market_value_estimate, arv
            - repair_estimate, expected_margin
            - bird_dog_score, propensity_to_sell
            - score_reasons (list of dicts)
        template: Template style ("default", "minimal", "detailed")

    Returns:
        PDF file as bytes

    Raises:
        Exception: If WeasyPrint not available or generation fails
    """
    if not WEASYPRINT_AVAILABLE:
        raise Exception("WeasyPrint not installed - cannot generate PDF")

    try:
        html_content = _render_memo_html(property_data, template)
        css_content = _get_memo_css(template)

        # Generate PDF
        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=css_content)]
        )

        logger.info(f"Generated property memo PDF for {property_data.get('address')}")

        return pdf_bytes

    except Exception as e:
        logger.error(f"Failed to generate property memo PDF: {str(e)}")
        raise


def generate_offer_packet(
    property_data: Dict[str, Any],
    deal_data: Dict[str, Any],
    comps: Optional[list] = None
) -> bytes:
    """
    Generate a comprehensive offer packet PDF

    Args:
        property_data: Property information
        deal_data: Deal/offer information including:
            - offer_price
            - arv, repair_cost
            - expected_margin
            - closing_timeline
        comps: List of comparable properties

    Returns:
        PDF file as bytes
    """
    if not WEASYPRINT_AVAILABLE:
        raise Exception("WeasyPrint not installed - cannot generate PDF")

    try:
        html_content = _render_offer_packet_html(property_data, deal_data, comps)
        css_content = _get_memo_css("detailed")

        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=css_content)]
        )

        logger.info(f"Generated offer packet PDF for {property_data.get('address')}")

        return pdf_bytes

    except Exception as e:
        logger.error(f"Failed to generate offer packet PDF: {str(e)}")
        raise


# ============================================================================
# HTML TEMPLATES
# ============================================================================

def _render_memo_html(property_data: Dict[str, Any], template: str) -> str:
    """
    Render HTML for property memo

    Creates a professional investment memo with:
    - Property details and photos
    - Financial analysis
    - Score breakdown with explanations
    - Market comparables
    - Risk factors
    """
    address = property_data.get("address", "Unknown Address")
    city = property_data.get("city", "")
    state = property_data.get("state", "")
    zip_code = property_data.get("zip_code", "")

    # Format currency
    def fmt_currency(val):
        if val is None:
            return "N/A"
        return f"${val:,.0f}"

    # Property characteristics
    beds = property_data.get("beds", "N/A")
    baths = property_data.get("baths", "N/A")
    sqft = property_data.get("sqft")
    sqft_str = f"{sqft:,}" if sqft else "N/A"
    year_built = property_data.get("year_built", "N/A")

    # Financial metrics
    assessed_value = fmt_currency(property_data.get("assessed_value"))
    market_value = fmt_currency(property_data.get("market_value_estimate"))
    arv = fmt_currency(property_data.get("arv"))
    repair_estimate = fmt_currency(property_data.get("repair_estimate"))

    # Scoring
    bird_dog_score = property_data.get("bird_dog_score", 0)
    score_pct = f"{bird_dog_score * 100:.0f}%" if bird_dog_score else "N/A"
    propensity = property_data.get("propensity_to_sell", 0)
    propensity_pct = f"{propensity * 100:.0f}%" if propensity else "N/A"

    # Score reasons
    score_reasons_html = ""
    for reason in property_data.get("score_reasons", [])[:5]:
        reason_text = reason.get("reason", "")
        weight = reason.get("weight", 0)
        weight_pct = f"{weight * 100:.0f}%"
        score_reasons_html += f"<li><strong>{reason_text}</strong> (weight: {weight_pct})</li>\n"

    if not score_reasons_html:
        score_reasons_html = "<li>No specific score factors available</li>"

    # Generate date
    today = datetime.now().strftime("%B %d, %Y")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Investment Memo - {address}</title>
    </head>
    <body>
        <div class="header">
            <h1>Investment Property Memo</h1>
            <p class="date">Generated: {today}</p>
        </div>

        <div class="property-info">
            <h2>{address}</h2>
            <p class="location">{city}, {state} {zip_code}</p>
        </div>

        <div class="section">
            <h3>Property Characteristics</h3>
            <table class="data-table">
                <tr>
                    <td><strong>Bedrooms:</strong></td>
                    <td>{beds}</td>
                    <td><strong>Bathrooms:</strong></td>
                    <td>{baths}</td>
                </tr>
                <tr>
                    <td><strong>Square Feet:</strong></td>
                    <td>{sqft_str}</td>
                    <td><strong>Year Built:</strong></td>
                    <td>{year_built}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h3>Financial Analysis</h3>
            <table class="data-table">
                <tr>
                    <td><strong>Assessed Value:</strong></td>
                    <td>{assessed_value}</td>
                </tr>
                <tr>
                    <td><strong>Market Value (Est):</strong></td>
                    <td>{market_value}</td>
                </tr>
                <tr>
                    <td><strong>After Repair Value (ARV):</strong></td>
                    <td>{arv}</td>
                </tr>
                <tr>
                    <td><strong>Estimated Repairs:</strong></td>
                    <td>{repair_estimate}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h3>Investment Score</h3>
            <div class="score-box">
                <div class="score-value">{score_pct}</div>
                <div class="score-label">Bird Dog Score</div>
            </div>
            <div class="score-box">
                <div class="score-value">{propensity_pct}</div>
                <div class="score-label">Propensity to Sell</div>
            </div>
        </div>

        <div class="section">
            <h3>Score Factors</h3>
            <ul class="score-reasons">
                {score_reasons_html}
            </ul>
        </div>

        <div class="footer">
            <p>Generated by Real Estate OS | Confidential Information</p>
        </div>
    </body>
    </html>
    """

    return html


def _render_offer_packet_html(
    property_data: Dict[str, Any],
    deal_data: Dict[str, Any],
    comps: Optional[list]
) -> str:
    """
    Render HTML for comprehensive offer packet
    """
    # Similar to memo but with additional deal terms and comps
    memo_html = _render_memo_html(property_data, "detailed")

    # Add deal terms section
    offer_price = deal_data.get("offer_price")
    offer_str = f"${offer_price:,.0f}" if offer_price else "TBD"

    deal_section = f"""
    <div class="section">
        <h3>Offer Terms</h3>
        <table class="data-table">
            <tr>
                <td><strong>Offer Price:</strong></td>
                <td>{offer_str}</td>
            </tr>
            <tr>
                <td><strong>Closing Timeline:</strong></td>
                <td>{deal_data.get('closing_timeline', '30 days')}</td>
            </tr>
            <tr>
                <td><strong>Contingencies:</strong></td>
                <td>{deal_data.get('contingencies', 'Standard inspection, financing')}</td>
            </tr>
        </table>
    </div>
    """

    # Insert before footer
    html = memo_html.replace('<div class="footer">', deal_section + '<div class="footer">')

    return html


def _get_memo_css(template: str) -> str:
    """
    Get CSS stylesheet for memo

    Professional styling with print optimization
    """
    return """
    @page {
        size: letter;
        margin: 1in;
    }

    body {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }

    .header {
        text-align: center;
        border-bottom: 3px solid #2c3e50;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }

    .header h1 {
        font-size: 24pt;
        color: #2c3e50;
        margin: 0 0 10px 0;
    }

    .date {
        color: #7f8c8d;
        font-size: 10pt;
    }

    .property-info {
        margin-bottom: 30px;
    }

    .property-info h2 {
        font-size: 18pt;
        color: #34495e;
        margin: 0 0 5px 0;
    }

    .location {
        font-size: 12pt;
        color: #7f8c8d;
        margin: 0;
    }

    .section {
        margin-bottom: 30px;
        page-break-inside: avoid;
    }

    .section h3 {
        font-size: 14pt;
        color: #2c3e50;
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 5px;
        margin-bottom: 15px;
    }

    .data-table {
        width: 100%;
        border-collapse: collapse;
    }

    .data-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #ecf0f1;
    }

    .data-table td:nth-child(odd) {
        width: 35%;
    }

    .score-box {
        display: inline-block;
        width: 45%;
        text-align: center;
        padding: 20px;
        margin: 10px 2%;
        background: #ecf0f1;
        border-radius: 8px;
    }

    .score-value {
        font-size: 32pt;
        font-weight: bold;
        color: #27ae60;
    }

    .score-label {
        font-size: 10pt;
        color: #7f8c8d;
        margin-top: 5px;
    }

    .score-reasons {
        list-style-type: disc;
        padding-left: 30px;
    }

    .score-reasons li {
        margin-bottom: 10px;
    }

    .footer {
        margin-top: 50px;
        text-align: center;
        font-size: 9pt;
        color: #95a5a6;
        border-top: 1px solid #bdc3c7;
        padding-top: 20px;
    }
    """
