"""Template rendering with MJML and Jinja2

Handles template loading, variable substitution, and MJML → HTML conversion.
"""
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path
import subprocess
import tempfile
import json
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Renders MJML templates with property data

    Process:
    1. Load MJML template from file
    2. Perform variable substitution using Python string formatting
    3. Convert MJML to responsive HTML using mjml CLI
    """

    def __init__(self, templates_dir: str = "/app/templates"):
        """
        Initialize template renderer

        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = Path(templates_dir)

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")

        logger.info(f"TemplateRenderer initialized with templates_dir: {templates_dir}")

    def render_investor_memo(self, property_data: Dict[str, Any]) -> str:
        """
        Render investor memo MJML template to HTML

        Args:
            property_data: Dictionary with all property data

        Returns:
            Rendered HTML string
        """
        logger.info(f"Rendering investor memo for property: {property_data.get('address', 'Unknown')}")

        # Load MJML template
        template_path = self.templates_dir / "investor_memo.mjml"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            mjml_template = f.read()

        # Prepare template variables
        template_vars = self._prepare_template_vars(property_data)

        # Substitute variables in MJML
        try:
            mjml_rendered = mjml_template.format(**template_vars)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise ValueError(f"Missing required template variable: {e}")

        # Convert MJML to HTML
        html = self._mjml_to_html(mjml_rendered)

        logger.info("Investor memo rendered successfully")

        return html

    def _prepare_template_vars(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and format template variables

        Handles:
        - Missing data (provides defaults)
        - Number formatting
        - Date formatting
        - Derived calculations
        """
        # Extract nested data
        prospect = property_data.get('prospect', {})
        enrichment = property_data.get('enrichment', {})
        score_data = property_data.get('score', {})
        census = property_data.get('census', {})
        payload = prospect.get('payload', {})

        # Calculate derived values
        score = score_data.get('bird_dog_score', 0)
        score_class = self._get_score_class(score)

        listing_price = float(payload.get('price', 0) or 0)
        assessed_value = float(enrichment.get('assessed_value', 0) or 0)
        market_value = float(enrichment.get('market_value', 0) or 0)

        square_footage = enrichment.get('square_footage', 0) or 0
        price_per_sqft = listing_price / square_footage if square_footage > 0 else 0

        last_sale_price = float(enrichment.get('last_sale_price', 0) or 0)
        price_appreciation = 0
        if last_sale_price > 0 and listing_price > 0:
            price_appreciation = ((listing_price - last_sale_price) / last_sale_price) * 100

        market_to_assessed_ratio = market_value / assessed_value if assessed_value > 0 else 1.0

        # Calculate potential ROI (simplified)
        potential_roi = 0
        if assessed_value > 0 and listing_price > 0:
            discount = ((assessed_value - listing_price) / assessed_value) * 100
            potential_roi = max(0, discount)

        # Calculate age
        year_built = enrichment.get('year_built')
        age_years = 0
        if year_built:
            age_years = datetime.now().year - year_built

        # Calculate years owned
        last_sale_date = enrichment.get('last_sale_date')
        years_owned = 0
        if last_sale_date:
            if isinstance(last_sale_date, str):
                try:
                    last_sale_date = datetime.strptime(last_sale_date, '%Y-%m-%d').date()
                except:
                    pass
            if isinstance(last_sale_date, date):
                years_owned = (datetime.now().date() - last_sale_date).days // 365

        # Generate opportunity description
        opportunity_description = self._generate_opportunity_description(
            property_data, score, potential_roi
        )

        # Format comparable properties
        comparable_properties = self._format_comparable_properties(
            property_data.get('comparables', [])
        )

        # Format feature importance
        feature_importance = self._format_feature_importance(
            score_data.get('feature_vector', [])
        )

        # Build template variables dictionary
        template_vars = {
            # Address
            'address': payload.get('address', 'Unknown Address'),
            'city': payload.get('city', ''),
            'state': payload.get('state', ''),
            'zip_code': payload.get('zip_code', ''),

            # Score
            'score': int(score),
            'score_class': score_class,
            'confidence_level': int(score_data.get('confidence_level', 0) or 0),

            # Pricing
            'listing_price': listing_price,
            'assessed_value': assessed_value,
            'market_value': market_value,
            'potential_roi': f"{potential_roi:.1f}",

            # Property details
            'bedrooms': enrichment.get('bedrooms', 0) or 0,
            'bathrooms': enrichment.get('bathrooms', 0) or 0,
            'square_footage': square_footage,
            'lot_size_sqft': enrichment.get('lot_size_sqft', 0) or 0,
            'year_built': year_built or 'Unknown',
            'property_type': enrichment.get('property_type', 'Unknown'),
            'age_years': age_years,

            # Financial
            'price_per_sqft': price_per_sqft,
            'last_sale_date': str(last_sale_date) if last_sale_date else 'Unknown',
            'last_sale_price': last_sale_price,
            'price_appreciation': f"{price_appreciation:.1f}",
            'tax_amount_annual': float(enrichment.get('tax_amount_annual', 0) or 0),
            'market_to_assessed_ratio': market_to_assessed_ratio,

            # Location
            'zip_population': census.get('population', 0) or 0,
            'zip_median_income': float(census.get('median_household_income', 0) or 0),
            'zip_median_home_value': float(census.get('median_home_value', 0) or 0),
            'owner_occupied_rate': f"{float(census.get('owner_occupied_rate', 0) or 0):.1f}",

            # Owner
            'owner_name': enrichment.get('owner_name', 'Unknown'),
            'owner_mailing_address': enrichment.get('owner_mailing_address', 'Unknown'),
            'years_owned': years_owned,

            # Property details
            'zoning': enrichment.get('zoning', 'Unknown'),
            'apn': enrichment.get('apn', 'Unknown'),

            # Content
            'opportunity_description': opportunity_description,
            'comparable_properties': comparable_properties,
            'feature_importance': feature_importance,

            # Metadata
            'source_api': enrichment.get('source_api', 'Unknown'),
            'listing_source': prospect.get('source', 'Unknown'),
            'model_version': score_data.get('model_version', 'Unknown'),
            'listing_url': prospect.get('url', '#'),
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        return template_vars

    @staticmethod
    def _get_score_class(score: float) -> str:
        """Get CSS class based on score"""
        if score >= 75:
            return 'score-excellent'
        elif score >= 60:
            return 'score-good'
        elif score >= 40:
            return 'score-fair'
        else:
            return 'score-poor'

    def _generate_opportunity_description(
        self,
        property_data: Dict[str, Any],
        score: float,
        potential_roi: float
    ) -> str:
        """Generate investment opportunity description"""
        prospect = property_data.get('prospect', {})
        enrichment = property_data.get('enrichment', {})
        payload = prospect.get('payload', {})

        bedrooms = enrichment.get('bedrooms', 0)
        bathrooms = enrichment.get('bathrooms', 0)
        city = payload.get('city', 'this market')
        property_type = enrichment.get('property_type', 'property')

        # Build description based on score
        if score >= 75:
            opening = f"Exceptional investment opportunity in {city}!"
        elif score >= 60:
            opening = f"Strong investment opportunity in {city}."
        else:
            opening = f"Potential investment opportunity in {city}."

        description = f"{opening} This {bedrooms} bedroom, {bathrooms} bathroom {property_type} "

        if potential_roi > 10:
            description += f"offers significant upside potential with an estimated {potential_roi:.1f}% ROI. "
        elif potential_roi > 5:
            description += f"presents solid value with an estimated {potential_roi:.1f}% ROI. "
        else:
            description += "is available for consideration. "

        description += "Our AI-powered analysis has evaluated this property across 35 factors including "
        description += "property characteristics, financial metrics, market conditions, and location demographics "
        description += "to provide you with data-driven insights."

        return description

    def _format_comparable_properties(self, comparables: list) -> str:
        """Format comparable properties HTML"""
        if not comparables:
            return '<mj-text font-size="14px" color="#6b7280">No comparable properties found.</mj-text>'

        html_parts = []

        for comp in comparables[:3]:  # Top 3 comparables
            similarity = comp.get('similarity_score', 0) * 100
            comp_data = comp.get('property', {})

            html_parts.append(f"""
<div style="border: 1px solid #e5e7eb; padding: 15px; margin-bottom: 10px; border-radius: 8px;">
    <strong>{comp_data.get('address', 'Unknown')}</strong><br/>
    Similarity: {similarity:.1f}% |
    {comp_data.get('bedrooms', 0)} bed, {comp_data.get('bathrooms', 0)} bath |
    {comp_data.get('square_footage', 0):,} sqft<br/>
    Price: ${comp_data.get('listing_price', 0):,.0f}
</div>
            """.strip())

        return '\n'.join(html_parts) if html_parts else 'No comparables available.'

    def _format_feature_importance(self, feature_vector: list) -> str:
        """Format feature importance (simplified for now)"""
        # In production, this would come from the ML model's feature importance
        # For now, return a placeholder
        return """
1. Price per Square Foot<br/>
2. Market to Assessed Value Ratio<br/>
3. Location Demographics<br/>
4. Property Age and Condition<br/>
5. Recent Sales Activity
        """.strip()

    def _mjml_to_html(self, mjml: str) -> str:
        """
        Convert MJML to HTML using mjml CLI

        Args:
            mjml: MJML string

        Returns:
            HTML string
        """
        try:
            # Write MJML to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mjml', delete=False) as f:
                mjml_file = f.name
                f.write(mjml)

            # Run mjml CLI
            result = subprocess.run(
                ['npx', 'mjml', mjml_file, '-s'],  # -s for stdin/stdout mode
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up temp file
            os.unlink(mjml_file)

            if result.returncode != 0:
                logger.error(f"MJML conversion failed: {result.stderr}")
                raise RuntimeError(f"MJML conversion failed: {result.stderr}")

            html = result.stdout

            logger.info("MJML converted to HTML successfully")

            return html

        except FileNotFoundError:
            logger.error("mjml CLI not found. Install with: npm install -g mjml")
            raise RuntimeError("mjml CLI not installed")

        except subprocess.TimeoutExpired:
            logger.error("MJML conversion timed out")
            raise RuntimeError("MJML conversion timed out")

        except Exception as e:
            logger.error(f"MJML conversion error: {e}")
            raise
