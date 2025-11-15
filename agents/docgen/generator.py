"""PDF generator for investor memos using MJML templates."""

import os
import subprocess
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


class InvestorMemoGenerator:
    """Generates investor memo PDFs from property data."""

    TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"
    OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "documents"

    def __init__(self):
        """Initialize the generator and ensure output directory exists."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_memo(self, property_data: dict, enrichment_data: dict, score_data: dict) -> str:
        """
        Generate an investor memo PDF for a property.

        Args:
            property_data: Property details from the database
            enrichment_data: Enrichment data (assessor, market, etc.)
            score_data: Investment scoring data

        Returns:
            Path to the generated PDF file
        """
        # Prepare template variables
        template_vars = self._prepare_template_vars(property_data, enrichment_data, score_data)

        # Read MJML template
        template_path = self.TEMPLATE_DIR / "investor_memo.mjml"
        with open(template_path, 'r', encoding='utf-8') as f:
            mjml_content = f.read()

        # Replace template variables
        html_content = self._render_template(mjml_content, template_vars)

        # Generate PDF filename
        property_id = property_data['id']
        filename = f"investor_memo_{property_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = self.OUTPUT_DIR / filename

        # Convert HTML to PDF using weasyprint
        self._html_to_pdf(html_content, str(pdf_path))

        return str(pdf_path)

    def _prepare_template_vars(self, property_data: dict, enrichment_data: dict, score_data: dict) -> Dict[str, str]:
        """Prepare all template variables for rendering."""
        # Determine score class for color coding
        total_score = score_data.get('total_score', 0)
        if total_score >= 80:
            score_class = 'score-high'
        elif total_score >= 60:
            score_class = 'score-medium'
        else:
            score_class = 'score-low'

        # Format features list
        features = property_data.get('features', [])
        features_str = ', '.join(features) if features else 'N/A'

        # Format risk factors
        risk_factors = score_data.get('risk_factors', [])
        risk_factors_str = '; '.join(risk_factors) if risk_factors else 'No significant risks identified'

        # Get score breakdown
        breakdown = score_data.get('score_breakdown', {})
        features_obj = score_data.get('features', {})

        return {
            # Property basics
            'address': property_data.get('address', 'N/A'),
            'city': property_data.get('city', 'N/A'),
            'state': property_data.get('state', 'N/A'),
            'zip_code': property_data.get('zip_code', 'N/A'),
            'price': f"{property_data.get('price', 0):,.0f}",
            'property_type': property_data.get('property_type', 'N/A').replace('_', ' ').title(),
            'bedrooms': str(property_data.get('bedrooms') or 'N/A'),
            'bathrooms': str(property_data.get('bathrooms') or 'N/A'),
            'sqft': f"{property_data.get('sqft', 0):,}" if property_data.get('sqft') else 'N/A',
            'year_built': str(property_data.get('year_built') or 'N/A'),
            'description': property_data.get('description', 'No description available.'),
            'features': features_str,

            # Investment score
            'total_score': str(total_score),
            'score_class': score_class,
            'recommendation': score_data.get('recommendation', 'N/A').replace('_', ' ').upper(),
            'recommendation_reason': score_data.get('recommendation_reason', 'N/A'),
            'risk_level': score_data.get('risk_level', 'N/A').upper(),
            'risk_factors': risk_factors_str,

            # Score breakdown
            'price_score': str(breakdown.get('price_score', 0)),
            'investment_metrics_score': str(breakdown.get('investment_metrics_score', 0)),
            'location_quality_score': str(breakdown.get('location_quality_score', 0)),
            'property_condition_score': str(breakdown.get('property_condition_score', 0)),

            # Investment metrics
            'cap_rate': f"{features_obj.get('cap_rate', 0):.2f}",
            'cash_on_cash_return': f"{features_obj.get('cash_on_cash_return', 0):.2f}",
            'monthly_rent': f"{features_obj.get('estimated_monthly_rent', 0):,.0f}",
            'gross_yield': f"{features_obj.get('gross_yield', 0):.2f}",

            # Market & location data
            'school_rating': str(enrichment_data.get('school_rating') or 'N/A'),
            'walkability_score': str(enrichment_data.get('walkability_score') or 'N/A'),
            'crime_rate': enrichment_data.get('crime_rate', 'N/A'),
            'median_rent': f"{enrichment_data.get('median_rent', 0):,.0f}" if enrichment_data.get('median_rent') else 'N/A',

            # Metadata
            'generated_date': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        }

    def _render_template(self, mjml_content: str, variables: Dict[str, str]) -> str:
        """
        Render MJML template with variables.

        For demo purposes, we'll convert MJML to HTML using mjml CLI if available,
        otherwise fall back to simple HTML generation.
        """
        # Replace all template variables
        content = mjml_content
        for key, value in variables.items():
            content = content.replace(f'{{{key}}}', value)

        # Try to convert MJML to HTML using mjml CLI
        try:
            # Create a temporary file for MJML
            temp_mjml = self.OUTPUT_DIR / "temp.mjml"
            with open(temp_mjml, 'w', encoding='utf-8') as f:
                f.write(content)

            # Run mjml command
            result = subprocess.run(
                ['npx', 'mjml', str(temp_mjml)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                html_content = result.stdout
                temp_mjml.unlink()  # Clean up temp file
                return html_content
            else:
                print(f"MJML conversion failed: {result.stderr}")
                # Fall back to simple HTML
                return self._mjml_to_simple_html(content, variables)

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"MJML CLI not available or failed: {e}")
            # Fall back to simple HTML
            return self._mjml_to_simple_html(content, variables)

    def _mjml_to_simple_html(self, mjml_content: str, variables: Dict[str, str]) -> str:
        """
        Fallback: Convert MJML-like content to simple HTML for PDF generation.
        This is a simplified converter for demo purposes.
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Investment Opportunity - {variables['address']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f3f4f6;
        }}
        .header {{
            background-color: #2563eb;
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .section-alt {{
            background-color: #f9fafb;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
        }}
        h1 {{
            margin: 0;
            font-size: 32px;
        }}
        h2 {{
            color: #111827;
            font-size: 18px;
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 8px;
        }}
        .score {{
            text-align: center;
            font-size: 64px;
            font-weight: bold;
            color: {variables.get('score_class', 'black').replace('score-high', '#10b981').replace('score-medium', '#f59e0b').replace('score-low', '#ef4444')};
            margin: 20px 0;
        }}
        .recommendation {{
            text-align: center;
            font-size: 18px;
            font-weight: bold;
            color: #2563eb;
            margin: 10px 0;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}
        .metrics-4col {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}
        .metric {{
            padding: 10px;
        }}
        .metric-label {{
            color: #6b7280;
            font-size: 12px;
            margin-bottom: 5px;
        }}
        .metric-value {{
            color: #111827;
            font-size: 16px;
            font-weight: 600;
        }}
        .footer {{
            background-color: #1f2937;
            color: #9ca3af;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            border-radius: 8px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>INVESTMENT OPPORTUNITY</h1>
        <p>Confidential Investment Memo</p>
    </div>

    <div class="section">
        <h2>{variables['address']}</h2>
        <p style="color: #6b7280;">{variables['city']}, {variables['state']} {variables['zip_code']}</p>
    </div>

    <div class="section-alt">
        <p style="text-align: center; color: #6b7280; font-size: 14px;">INVESTMENT SCORE</p>
        <div class="score">{variables['total_score']}</div>
        <p style="text-align: center; color: #9ca3af; font-size: 12px;">out of 100</p>
        <div class="recommendation">{variables['recommendation']}</div>
    </div>

    <div class="section">
        <h2>Key Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Listing Price</div>
                <div class="metric-value">${variables['price']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Property Type</div>
                <div class="metric-value">{variables['property_type']}</div>
            </div>
        </div>
        <div class="metrics-4col">
            <div class="metric">
                <div class="metric-label">Bedrooms</div>
                <div class="metric-value">{variables['bedrooms']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Bathrooms</div>
                <div class="metric-value">{variables['bathrooms']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Square Feet</div>
                <div class="metric-value">{variables['sqft']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Year Built</div>
                <div class="metric-value">{variables['year_built']}</div>
            </div>
        </div>
    </div>

    <div class="section-alt">
        <h2>Investment Analysis</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Cap Rate</div>
                <div class="metric-value">{variables['cap_rate']}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Cash on Cash Return</div>
                <div class="metric-value">{variables['cash_on_cash_return']}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Monthly Rent Estimate</div>
                <div class="metric-value">${variables['monthly_rent']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Gross Yield</div>
                <div class="metric-value">{variables['gross_yield']}%</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Market & Location Data</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">School Rating</div>
                <div class="metric-value">{variables['school_rating']}/10</div>
            </div>
            <div class="metric">
                <div class="metric-label">Walk Score</div>
                <div class="metric-value">{variables['walkability_score']}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Crime Rate</div>
                <div class="metric-value">{variables['crime_rate']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Median Area Rent</div>
                <div class="metric-value">${variables['median_rent']}</div>
            </div>
        </div>
    </div>

    <div class="section-alt">
        <h2>Score Breakdown</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Price Analysis</div>
                <div class="metric-value">{variables['price_score']}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Investment Metrics</div>
                <div class="metric-value">{variables['investment_metrics_score']}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Location Quality</div>
                <div class="metric-value">{variables['location_quality_score']}/100</div>
            </div>
            <div class="metric">
                <div class="metric-label">Property Condition</div>
                <div class="metric-value">{variables['property_condition_score']}/100</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Risk Assessment</h2>
        <div class="metric-label">Risk Level</div>
        <p style="font-size: 18px; font-weight: bold; color: #f59e0b;">{variables['risk_level']}</p>
        <p style="color: #6b7280; margin-top: 10px;">{variables['risk_factors']}</p>
    </div>

    <div class="section-alt">
        <h2>Recommendation</h2>
        <p style="color: #4b5563;">{variables['recommendation_reason']}</p>
    </div>

    <div class="section">
        <h2>Property Features</h2>
        <p style="color: #4b5563;">{variables['features']}</p>
    </div>

    <div class="section-alt">
        <h2>Property Description</h2>
        <p style="color: #4b5563;">{variables['description']}</p>
    </div>

    <div class="footer">
        <p>Generated by Real Estate OS - Investment Analysis Platform</p>
        <p>{variables['generated_date']}</p>
        <p style="color: #6b7280; margin-top: 10px;">This document is confidential and intended solely for investment analysis purposes.</p>
    </div>
</body>
</html>
"""
        return html

    def _html_to_pdf(self, html_content: str, output_path: str):
        """Convert HTML content to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML, CSS

            # Convert HTML to PDF
            HTML(string=html_content).write_pdf(output_path)

        except ImportError:
            # If WeasyPrint is not available, try using pdfkit/wkhtmltopdf
            try:
                import pdfkit
                pdfkit.from_string(html_content, output_path)
            except (ImportError, OSError):
                # If no PDF library is available, save as HTML for now
                print("Warning: No PDF library available. Saving as HTML.")
                html_path = output_path.replace('.pdf', '.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"Saved HTML to: {html_path}")
