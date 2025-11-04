"""
Mock PDF Generation (WeasyPrint alternative)

Generates simple text-based PDFs for demo mode without WeasyPrint dependencies.
Returns mock PDF content with realistic structure.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import io

logger = logging.getLogger(__name__)

# ============================================================================
# SIMPLE PDF GENERATION (Mock)
# ============================================================================

def _create_simple_pdf_content(title: str, content_lines: list) -> bytes:
    """
    Create a simple mock PDF with text content

    In production, this would use WeasyPrint to generate real PDFs from HTML.
    For mock/demo mode, we generate a simple text representation.

    Args:
        title: PDF title
        content_lines: Lines of content to include

    Returns:
        PDF content as bytes (simplified mock format)
    """
    # Create a simple PDF-like structure
    # In reality, this would be a proper PDF binary format
    pdf_content = f"""%%PDF-1.4
%Mock PDF Document
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 0
>>
stream
{title}
{'=' * len(title)}

{chr(10).join(content_lines)}

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
[MOCK PDF - For Demo Purposes Only]
endstream
endobj

xref
0 5
0000000000 65535 f
0000000015 00000 n
0000000074 00000 n
0000000133 00000 n
0000000237 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
500
%%EOF
"""

    return pdf_content.encode('utf-8')


# ============================================================================
# PROPERTY MEMO GENERATION
# ============================================================================

def generate_property_memo(
    property_data: Dict[str, Any],
    template: str = "default",
    include_photos: bool = True,
    include_comps: bool = True
) -> Dict[str, Any]:
    """
    Mock generate property investment memo PDF

    Args:
        property_data: Property details (address, price, description, etc.)
        template: Template style to use
        include_photos: Whether to include property photos
        include_comps: Whether to include comparable properties

    Returns:
        Dict with PDF content, filename, and metadata
    """
    address = property_data.get("address", "Unknown Property")
    price = property_data.get("asking_price", 0)
    beds = property_data.get("beds", "N/A")
    baths = property_data.get("baths", "N/A")
    sqft = property_data.get("sqft", "N/A")
    description = property_data.get("description", "No description available")

    # Build content lines
    content_lines = [
        f"Property Address: {address}",
        "",
        "PROPERTY DETAILS",
        "-" * 50,
        f"Asking Price: ${price:,}" if isinstance(price, (int, float)) else f"Asking Price: {price}",
        f"Bedrooms: {beds}",
        f"Bathrooms: {baths}",
        f"Square Feet: {sqft}",
        "",
        "DESCRIPTION",
        "-" * 50,
        description,
        "",
        "INVESTMENT ANALYSIS",
        "-" * 50,
        f"Estimated ARV: ${int(price * 1.3):,}" if isinstance(price, (int, float)) else "N/A",
        f"Estimated Rehab: ${int(price * 0.15):,}" if isinstance(price, (int, float)) else "N/A",
        f"Projected Profit: ${int(price * 0.15):,}" if isinstance(price, (int, float)) else "N/A",
        "",
    ]

    if include_comps:
        content_lines.extend([
            "COMPARABLE PROPERTIES",
            "-" * 50,
            "1. 123 Similar St - $250,000 - 3bd/2ba - Sold 30 days ago",
            "2. 456 Nearby Ave - $265,000 - 3bd/2ba - Sold 45 days ago",
            "3. 789 Close Rd - $242,000 - 3bd/1.5ba - Sold 60 days ago",
            "",
        ])

    if include_photos:
        content_lines.extend([
            "PHOTOS",
            "-" * 50,
            "[Front exterior photo]",
            "[Kitchen photo]",
            "[Bathroom photo]",
            "",
        ])

    # Generate PDF content
    title = f"Investment Memo - {address}"
    pdf_bytes = _create_simple_pdf_content(title, content_lines)

    # Generate filename
    safe_address = address.replace(" ", "_").replace(",", "")
    filename = f"memo_{safe_address}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    logger.info(f"[MOCK] Generated property memo PDF: {filename} ({len(pdf_bytes)} bytes)")

    return {
        "success": True,
        "pdf_content": pdf_bytes,
        "filename": filename,
        "content_type": "application/pdf",
        "size": len(pdf_bytes),
        "template": template,
        "property_id": property_data.get("id"),
        "generated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# OFFER PACKET GENERATION
# ============================================================================

def generate_offer_packet(
    property_data: Dict[str, Any],
    deal_data: Dict[str, Any],
    investor_data: Optional[Dict[str, Any]] = None,
    include_contract: bool = True,
    include_disclosures: bool = True
) -> Dict[str, Any]:
    """
    Mock generate investor offer packet PDF

    Args:
        property_data: Property details
        deal_data: Deal terms (offer price, closing date, etc.)
        investor_data: Investor/buyer information
        include_contract: Whether to include purchase contract
        include_disclosures: Whether to include disclosure forms

    Returns:
        Dict with PDF content, filename, and metadata
    """
    address = property_data.get("address", "Unknown Property")
    offer_price = deal_data.get("offer_price", 0)
    closing_date = deal_data.get("closing_date", "TBD")
    earnest_money = deal_data.get("earnest_money", 0)
    contingencies = deal_data.get("contingencies", [])

    investor_name = "Potential Buyer"
    if investor_data:
        investor_name = investor_data.get("name", investor_name)

    # Build content lines
    content_lines = [
        f"Property: {address}",
        f"Prepared For: {investor_name}",
        f"Date: {datetime.utcnow().strftime('%B %d, %Y')}",
        "",
        "OFFER SUMMARY",
        "=" * 50,
        f"Offer Price: ${offer_price:,}" if isinstance(offer_price, (int, float)) else f"Offer Price: {offer_price}",
        f"Earnest Money: ${earnest_money:,}" if isinstance(earnest_money, (int, float)) else f"Earnest Money: {earnest_money}",
        f"Proposed Closing Date: {closing_date}",
        "",
        "CONTINGENCIES",
        "-" * 50,
    ]

    if contingencies:
        for i, contingency in enumerate(contingencies, 1):
            content_lines.append(f"{i}. {contingency}")
    else:
        content_lines.append("- Inspection contingency (10 days)")
        content_lines.append("- Financing contingency (30 days)")
        content_lines.append("- Appraisal contingency")

    content_lines.extend([
        "",
        "PROPERTY DETAILS",
        "-" * 50,
        f"Address: {address}",
        f"Bedrooms: {property_data.get('beds', 'N/A')}",
        f"Bathrooms: {property_data.get('baths', 'N/A')}",
        f"Square Feet: {property_data.get('sqft', 'N/A')}",
        f"Year Built: {property_data.get('year_built', 'N/A')}",
        "",
    ])

    if include_contract:
        content_lines.extend([
            "PURCHASE CONTRACT",
            "=" * 50,
            "1. PARTIES",
            f"   Buyer: {investor_name}",
            "   Seller: [Property Owner]",
            "",
            "2. PROPERTY DESCRIPTION",
            f"   {address}",
            "",
            "3. PURCHASE PRICE AND TERMS",
            f"   Purchase Price: ${offer_price:,}" if isinstance(offer_price, (int, float)) else "N/A",
            f"   Earnest Money Deposit: ${earnest_money:,}" if isinstance(earnest_money, (int, float)) else "N/A",
            f"   Closing Date: {closing_date}",
            "",
            "4. TITLE AND CLOSING",
            "   Title company to be determined",
            "   Seller to provide clear title",
            "",
        ])

    if include_disclosures:
        content_lines.extend([
            "DISCLOSURES",
            "=" * 50,
            "- Lead-based paint disclosure (if applicable)",
            "- Property condition disclosure",
            "- Homeowners association disclosure (if applicable)",
            "- Natural hazard disclosure",
            "",
        ])

    content_lines.extend([
        "NEXT STEPS",
        "-" * 50,
        "1. Review and sign the offer",
        "2. Submit earnest money deposit",
        "3. Schedule property inspection",
        "4. Secure financing (if applicable)",
        "5. Review final closing documents",
        "",
        "[MOCK DOCUMENT - For Demo Purposes Only]",
    ])

    # Generate PDF content
    title = f"Offer Packet - {address}"
    pdf_bytes = _create_simple_pdf_content(title, content_lines)

    # Generate filename
    safe_address = address.replace(" ", "_").replace(",", "")
    filename = f"offer_packet_{safe_address}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    logger.info(f"[MOCK] Generated offer packet PDF: {filename} ({len(pdf_bytes)} bytes)")

    return {
        "success": True,
        "pdf_content": pdf_bytes,
        "filename": filename,
        "content_type": "application/pdf",
        "size": len(pdf_bytes),
        "property_id": property_data.get("id"),
        "deal_id": deal_data.get("id"),
        "investor_id": investor_data.get("id") if investor_data else None,
        "generated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# CUSTOM PDF GENERATION
# ============================================================================

def generate_custom_pdf(
    title: str,
    html_content: str,
    css: Optional[str] = None,
    footer: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock generate custom PDF from HTML

    In production, this would use WeasyPrint to render HTML/CSS to PDF.
    In mock mode, we extract text content from HTML.

    Args:
        title: PDF title
        html_content: HTML content to render
        css: Optional CSS styling
        footer: Optional footer content

    Returns:
        Dict with PDF content and metadata
    """
    # Simple HTML stripping (in production, would render with WeasyPrint)
    import re

    # Remove HTML tags for mock text content
    text_content = re.sub('<[^<]+?>', '', html_content)
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]

    if footer:
        lines.append("")
        lines.append("-" * 50)
        lines.append(footer)

    pdf_bytes = _create_simple_pdf_content(title, lines)

    filename = f"{title.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    logger.info(f"[MOCK] Generated custom PDF: {filename} ({len(pdf_bytes)} bytes)")

    return {
        "success": True,
        "pdf_content": pdf_bytes,
        "filename": filename,
        "content_type": "application/pdf",
        "size": len(pdf_bytes),
        "generated_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# BATCH PDF GENERATION
# ============================================================================

def generate_batch_memos(
    properties: list,
    template: str = "default"
) -> Dict[str, Any]:
    """
    Mock generate memos for multiple properties

    Args:
        properties: List of property data dicts
        template: Template to use for all memos

    Returns:
        Dict with list of generated PDFs
    """
    results = []

    for prop in properties:
        result = generate_property_memo(prop, template=template)
        results.append(result)

    logger.info(f"[MOCK] Generated {len(results)} property memos")

    return {
        "success": True,
        "count": len(results),
        "memos": results,
        "generated_at": datetime.utcnow().isoformat()
    }
