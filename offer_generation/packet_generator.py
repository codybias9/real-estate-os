"""
Offer Packet Generator.

Creates professional PDF offer packets containing:
- Property summary and photos
- Financial analysis (DCF, Comp-Critic)
- Hazard assessments
- Market comps
- Lease schedules
- Ownership structure
- Terms and conditions
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass
import io
import logging

logger = logging.getLogger(__name__)


@dataclass
class PropertySummary:
    """Property information for offer packet."""
    property_id: int
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str
    building_sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    units: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    parking_spaces: Optional[int] = None


@dataclass
class OfferTerms:
    """Offer terms and conditions."""
    offer_price: float
    earnest_money: float
    due_diligence_days: int
    closing_days: int
    financing_contingency: bool
    inspection_contingency: bool
    appraisal_contingency: bool
    seller_concessions: Optional[float] = None
    expiration_date: Optional[date] = None
    special_terms: Optional[str] = None


@dataclass
class FinancialAnalysis:
    """Financial analysis results."""
    purchase_price: float
    down_payment: float
    loan_amount: float
    interest_rate: float

    # DCF results
    irr: Optional[float] = None
    npv: Optional[float] = None
    dscr: Optional[float] = None
    exit_value: Optional[float] = None
    cash_on_cash_return: Optional[float] = None

    # Comp-Critic results
    estimated_value: Optional[float] = None
    comp_value_range: Optional[tuple] = None  # (low, high)

    # Hazards
    hazard_composite_score: Optional[float] = None
    hazard_value_adjustment: Optional[float] = None
    annual_hazard_costs: Optional[float] = None


class OfferPacketGenerator:
    """
    Generates professional PDF offer packets.

    Uses ReportLab for PDF generation with:
    - Cover page with property photo
    - Executive summary
    - Financial analysis section
    - Hazard assessment section
    - Comparable properties section
    - Lease schedule (for income properties)
    - Terms and conditions
    - Appendices
    """

    def __init__(self):
        self.title_font_size = 24
        self.heading_font_size = 16
        self.body_font_size = 11
        self.margin = 72  # 1 inch

    def generate_packet(
        self,
        property_summary: PropertySummary,
        offer_terms: OfferTerms,
        financial_analysis: FinancialAnalysis,
        hazard_data: Optional[Dict[str, Any]] = None,
        comps: Optional[List[Dict[str, Any]]] = None,
        leases: Optional[List[Dict[str, Any]]] = None,
        photos: Optional[List[bytes]] = None,
        buyer_info: Optional[Dict[str, str]] = None
    ) -> bytes:
        """
        Generate complete offer packet PDF.

        Args:
            property_summary: Property details
            offer_terms: Offer terms and conditions
            financial_analysis: Financial analysis results
            hazard_data: Hazard assessment data
            comps: Comparable properties
            leases: Lease schedules (for income properties)
            photos: Property photos
            buyer_info: Buyer contact information

        Returns:
            PDF bytes
        """
        logger.info(f"Generating offer packet for property {property_summary.property_id}")

        try:
            # For production: Use ReportLab to generate PDF
            # This is a simplified mock implementation

            pdf_content = self._generate_mock_pdf(
                property_summary=property_summary,
                offer_terms=offer_terms,
                financial_analysis=financial_analysis,
                hazard_data=hazard_data,
                comps=comps,
                leases=leases
            )

            logger.info("Offer packet generated successfully")
            return pdf_content

        except Exception as e:
            logger.error(f"Failed to generate offer packet: {e}")
            raise

    def _generate_mock_pdf(
        self,
        property_summary: PropertySummary,
        offer_terms: OfferTerms,
        financial_analysis: FinancialAnalysis,
        **kwargs
    ) -> bytes:
        """Generate mock PDF content (text representation)."""

        # Build text content
        content_lines = []

        # Cover page
        content_lines.extend([
            "=" * 80,
            "OFFER PACKET".center(80),
            "=" * 80,
            "",
            property_summary.address.center(80),
            f"{property_summary.city}, {property_summary.state} {property_summary.zip_code}".center(80),
            "",
            f"Generated: {datetime.now().strftime('%B %d, %Y')}".center(80),
            "",
            "=" * 80,
            "",
            ""
        ])

        # Executive Summary
        content_lines.extend([
            "EXECUTIVE SUMMARY",
            "-" * 80,
            "",
            f"Property Type:        {property_summary.property_type}",
            f"Address:              {property_summary.address}",
            f"Building Size:        {property_summary.building_sqft:,} sqft" if property_summary.building_sqft else "Building Size:        N/A",
            f"Lot Size:             {property_summary.lot_size_sqft:,} sqft" if property_summary.lot_size_sqft else "Lot Size:             N/A",
            f"Year Built:           {property_summary.year_built}" if property_summary.year_built else "",
            "",
            "OFFER TERMS",
            "-" * 40,
            f"Offer Price:          ${offer_terms.offer_price:,.0f}",
            f"Earnest Money:        ${offer_terms.earnest_money:,.0f} ({offer_terms.earnest_money/offer_terms.offer_price*100:.1f}%)",
            f"Due Diligence:        {offer_terms.due_diligence_days} days",
            f"Closing:              {offer_terms.closing_days} days",
            f"Financing:            {'Required' if offer_terms.financing_contingency else 'Cash'}",
            f"Inspection:           {'Contingent' if offer_terms.inspection_contingency else 'As-Is'}",
            "",
            ""
        ])

        # Financial Analysis
        content_lines.extend([
            "FINANCIAL ANALYSIS",
            "-" * 80,
            "",
            "Investment Structure:",
            f"  Purchase Price:     ${financial_analysis.purchase_price:,.0f}",
            f"  Down Payment:       ${financial_analysis.down_payment:,.0f} ({financial_analysis.down_payment/financial_analysis.purchase_price*100:.0f}%)",
            f"  Loan Amount:        ${financial_analysis.loan_amount:,.0f}",
            f"  Interest Rate:      {financial_analysis.interest_rate:.2%}",
            "",
        ])

        if financial_analysis.irr:
            content_lines.extend([
                "DCF Analysis:",
                f"  IRR:                {financial_analysis.irr:.2%}",
                f"  NPV:                ${financial_analysis.npv:,.0f}",
                f"  DSCR:               {financial_analysis.dscr:.2f}x",
                f"  Exit Value (5yr):   ${financial_analysis.exit_value:,.0f}",
                f"  Cash-on-Cash:       {financial_analysis.cash_on_cash_return:.2%}" if financial_analysis.cash_on_cash_return else "",
                "",
            ])

        if financial_analysis.estimated_value:
            content_lines.extend([
                "Comp-Critic Valuation:",
                f"  Estimated Value:    ${financial_analysis.estimated_value:,.0f}",
                f"  Value Range:        ${financial_analysis.comp_value_range[0]:,.0f} - ${financial_analysis.comp_value_range[1]:,.0f}" if financial_analysis.comp_value_range else "",
                f"  Offer vs Value:     {(offer_terms.offer_price/financial_analysis.estimated_value - 1)*100:+.1f}%",
                "",
            ])

        # Hazard Assessment
        if financial_analysis.hazard_composite_score is not None:
            content_lines.extend([
                "HAZARD ASSESSMENT",
                "-" * 80,
                "",
                f"Composite Hazard Score:     {financial_analysis.hazard_composite_score:.2f} / 1.0",
                "",
            ])

            if financial_analysis.hazard_composite_score < 0.3:
                risk_level = "LOW RISK"
            elif financial_analysis.hazard_composite_score < 0.6:
                risk_level = "MODERATE RISK"
            else:
                risk_level = "HIGH RISK"

            content_lines.extend([
                f"Risk Level:                 {risk_level}",
                f"Value Adjustment:           ${financial_analysis.hazard_value_adjustment:+,.0f} ({financial_analysis.hazard_value_adjustment/offer_terms.offer_price*100:+.1f}%)" if financial_analysis.hazard_value_adjustment else "",
                f"Annual Hazard Costs:        ${financial_analysis.annual_hazard_costs:,.0f}" if financial_analysis.annual_hazard_costs else "",
                "",
                ""
            ])

        # Comparable Properties
        if kwargs.get('comps'):
            content_lines.extend([
                "COMPARABLE PROPERTIES",
                "-" * 80,
                "",
                "Top 3 Comparable Sales:",
                ""
            ])

            for i, comp in enumerate(kwargs['comps'][:3], 1):
                content_lines.extend([
                    f"Comp #{i}:",
                    f"  Address:       {comp.get('address', 'N/A')}",
                    f"  Sale Price:    ${comp.get('sold_price', 0):,.0f}",
                    f"  Size:          {comp.get('sqft', 0):,} sqft",
                    f"  Price/sqft:    ${comp.get('sold_price', 0)/comp.get('sqft', 1):,.0f}",
                    f"  Sale Date:     {comp.get('sale_date', 'N/A')}",
                    ""
                ])

        # Lease Schedule
        if kwargs.get('leases'):
            content_lines.extend([
                "LEASE SCHEDULE",
                "-" * 80,
                "",
                f"Total Units: {len(kwargs['leases'])}",
                ""
            ])

            total_rent = sum(lease.get('monthly_rent', 0) for lease in kwargs['leases'])
            content_lines.append(f"Total Monthly Rent: ${total_rent:,.0f}")
            content_lines.append(f"Annual Gross Income: ${total_rent * 12:,.0f}")
            content_lines.append("")

        # Signature block
        content_lines.extend([
            "",
            "",
            "BUYER SIGNATURE",
            "-" * 80,
            "",
            "Signed: _________________________________    Date: ______________",
            "",
            "",
            "This offer is valid until " + (offer_terms.expiration_date.strftime("%B %d, %Y") if offer_terms.expiration_date else "specified date"),
            "",
            ""
        ])

        # Join all lines
        pdf_text = "\n".join(content_lines)

        # Return as bytes (in production, would return actual PDF bytes)
        return pdf_text.encode('utf-8')

    def save_packet(self, pdf_bytes: bytes, output_path: str):
        """Save PDF packet to file."""
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        logger.info(f"Offer packet saved to {output_path}")


def generate_offer_packet(
    property_data: Dict[str, Any],
    offer_data: Dict[str, Any],
    financial_data: Dict[str, Any],
    **kwargs
) -> bytes:
    """
    Convenience function to generate offer packet.

    Args:
        property_data: Property information dict
        offer_data: Offer terms dict
        financial_data: Financial analysis dict
        **kwargs: Additional data (hazards, comps, leases, photos)

    Returns:
        PDF bytes
    """
    # Convert dicts to dataclasses
    property_summary = PropertySummary(
        property_id=property_data['property_id'],
        address=property_data['address'],
        city=property_data['city'],
        state=property_data['state'],
        zip_code=property_data['zip_code'],
        property_type=property_data.get('property_type', 'Residential'),
        building_sqft=property_data.get('building_sqft'),
        lot_size_sqft=property_data.get('lot_size_sqft'),
        year_built=property_data.get('year_built'),
        units=property_data.get('units'),
        bedrooms=property_data.get('bedrooms'),
        bathrooms=property_data.get('bathrooms')
    )

    offer_terms = OfferTerms(
        offer_price=offer_data['offer_price'],
        earnest_money=offer_data.get('earnest_money', offer_data['offer_price'] * 0.01),
        due_diligence_days=offer_data.get('due_diligence_days', 14),
        closing_days=offer_data.get('closing_days', 30),
        financing_contingency=offer_data.get('financing_contingency', True),
        inspection_contingency=offer_data.get('inspection_contingency', True),
        appraisal_contingency=offer_data.get('appraisal_contingency', True),
        expiration_date=offer_data.get('expiration_date')
    )

    financial_analysis = FinancialAnalysis(
        purchase_price=financial_data['purchase_price'],
        down_payment=financial_data.get('down_payment', financial_data['purchase_price'] * 0.25),
        loan_amount=financial_data['purchase_price'] - financial_data.get('down_payment', financial_data['purchase_price'] * 0.25),
        interest_rate=financial_data.get('interest_rate', 0.065),
        irr=financial_data.get('irr'),
        npv=financial_data.get('npv'),
        dscr=financial_data.get('dscr'),
        exit_value=financial_data.get('exit_value'),
        estimated_value=financial_data.get('estimated_value'),
        comp_value_range=financial_data.get('comp_value_range'),
        hazard_composite_score=financial_data.get('hazard_composite_score'),
        hazard_value_adjustment=financial_data.get('hazard_value_adjustment'),
        annual_hazard_costs=financial_data.get('annual_hazard_costs')
    )

    generator = OfferPacketGenerator()

    return generator.generate_packet(
        property_summary=property_summary,
        offer_terms=offer_terms,
        financial_analysis=financial_analysis,
        hazard_data=kwargs.get('hazard_data'),
        comps=kwargs.get('comps'),
        leases=kwargs.get('leases'),
        photos=kwargs.get('photos'),
        buyer_info=kwargs.get('buyer_info')
    )


if __name__ == "__main__":
    # Test packet generation
    property_data = {
        'property_id': 123,
        'address': '456 Oak Avenue',
        'city': 'San Francisco',
        'state': 'CA',
        'zip_code': '94102',
        'property_type': 'Multifamily',
        'building_sqft': 12000,
        'lot_size_sqft': 8000,
        'year_built': 1985,
        'units': 12
    }

    offer_data = {
        'offer_price': 3200000,
        'earnest_money': 32000,
        'due_diligence_days': 21,
        'closing_days': 45
    }

    financial_data = {
        'purchase_price': 3200000,
        'down_payment': 800000,
        'interest_rate': 0.065,
        'irr': 0.142,
        'npv': 450000,
        'dscr': 1.35,
        'exit_value': 4200000,
        'estimated_value': 3150000,
        'comp_value_range': (3000000, 3300000),
        'hazard_composite_score': 0.45,
        'hazard_value_adjustment': -80000,
        'annual_hazard_costs': 18000
    }

    pdf_bytes = generate_offer_packet(
        property_data=property_data,
        offer_data=offer_data,
        financial_data=financial_data
    )

    print("Generated offer packet:")
    print(pdf_bytes.decode('utf-8'))
