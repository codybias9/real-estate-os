"""Email templates for investor outreach

Generates email bodies for different campaign types.
"""
import logging
from typing import Dict, Any
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailTemplates:
    """
    Email template manager

    Provides templates for:
    - Initial investor memo outreach
    - Follow-up emails
    - Property update notifications
    """

    @staticmethod
    def render_investor_memo_email(property_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Render investor memo email (HTML + plain text)

        Args:
            property_data: Property information dictionary

        Returns:
            Dictionary with 'html', 'plain', 'subject'
        """
        # Extract key data
        address = property_data.get('address', 'Unknown Address')
        city = property_data.get('city', '')
        state = property_data.get('state', '')
        score = int(property_data.get('score', 0))
        listing_price = property_data.get('listing_price', 0)
        bedrooms = property_data.get('bedrooms', 0)
        bathrooms = property_data.get('bathrooms', 0)
        potential_roi = property_data.get('potential_roi', 0)

        # Generate subject line
        subject = f"Investment Opportunity: {address} - Score {score}/100"

        # HTML template
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
    <style>
        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: #1f2937;
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .score-badge {
            background: #10b981;
            color: white;
            font-size: 32px;
            font-weight: bold;
            padding: 15px 25px;
            border-radius: 8px;
            display: inline-block;
            margin: 15px 0;
        }
        .content {
            background: #ffffff;
            padding: 30px;
            border: 1px solid #e5e7eb;
        }
        .property-details {
            background: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #d1d5db;
        }
        .detail-label {
            color: #6b7280;
            font-weight: 500;
        }
        .detail-value {
            color: #111827;
            font-weight: bold;
        }
        .cta-button {
            background: #3b82f6;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 8px;
            display: inline-block;
            margin: 20px 0;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            color: #6b7280;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0;">Investment Opportunity</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px;">{{ address }}</p>
        <p style="margin: 5px 0 0 0; color: #d1d5db;">{{ city }}, {{ state }}</p>
        <div class="score-badge">{{ score }}/100</div>
    </div>

    <div class="content">
        <p>Hi there,</p>

        <p>I wanted to share an exciting off-market property opportunity that our AI-powered
        analysis has identified as a strong investment prospect.</p>

        <div class="property-details">
            <div class="detail-row">
                <span class="detail-label">Listing Price</span>
                <span class="detail-value">${{ "{:,.0f}".format(listing_price) }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Property Type</span>
                <span class="detail-value">{{ bedrooms }} bed / {{ bathrooms }} bath</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Potential ROI</span>
                <span class="detail-value" style="color: #10b981;">{{ potential_roi }}%</span>
            </div>
        </div>

        <p><strong>Why This Property?</strong></p>

        <p>Our proprietary machine learning model has analyzed this property across 35 different
        factors including property characteristics, financial metrics, market conditions, and
        location demographics. The Bird-Dog Score of <strong>{{ score }}/100</strong> indicates
        this is a {{ score_label }} investment opportunity.</p>

        <p>I've attached a detailed investor memo with complete analysis including:</p>

        <ul>
            <li>Comprehensive property details and financial analysis</li>
            <li>Location demographics and market insights</li>
            <li>Comparable properties in the area</li>
            <li>AI-powered investment recommendations</li>
        </ul>

        <p style="text-align: center;">
            <a href="{{ listing_url }}" class="cta-button">View Full Analysis</a>
        </p>

        <p>Feel free to reach out if you'd like to discuss this opportunity further or if you'd
        like me to send you additional properties that match your investment criteria.</p>

        <p>Best regards,<br>
        {{ sender_name }}<br>
        Real Estate OS</p>
    </div>

    <div class="footer">
        <p>This email was sent because you expressed interest in real estate investment opportunities.<br>
        If you'd prefer not to receive these emails, please reply with "unsubscribe".</p>
    </div>
</body>
</html>
        """)

        # Plain text template
        plain_template = Template("""
Investment Opportunity: {{ address }}
{{ city }}, {{ state }}

Bird-Dog Score: {{ score }}/100

Hi there,

I wanted to share an exciting off-market property opportunity that our AI-powered
analysis has identified as a strong investment prospect.

PROPERTY DETAILS:
- Listing Price: ${{ "{:,.0f}".format(listing_price) }}
- Property: {{ bedrooms }} bed / {{ bathrooms }} bath
- Potential ROI: {{ potential_roi }}%

WHY THIS PROPERTY?

Our proprietary machine learning model has analyzed this property across 35 different
factors including property characteristics, financial metrics, market conditions, and
location demographics. The Bird-Dog Score of {{ score }}/100 indicates this is a
{{ score_label }} investment opportunity.

I've attached a detailed investor memo with complete analysis including:
- Comprehensive property details and financial analysis
- Location demographics and market insights
- Comparable properties in the area
- AI-powered investment recommendations

View the listing: {{ listing_url }}

Feel free to reach out if you'd like to discuss this opportunity further or if you'd
like me to send you additional properties that match your investment criteria.

Best regards,
{{ sender_name }}
Real Estate OS

---
This email was sent because you expressed interest in real estate investment opportunities.
If you'd prefer not to receive these emails, please reply with "unsubscribe".
        """)

        # Determine score label
        if score >= 75:
            score_label = "exceptional"
        elif score >= 60:
            score_label = "strong"
        elif score >= 40:
            score_label = "solid"
        else:
            score_label = "potential"

        # Template context
        context = {
            'address': address,
            'city': city,
            'state': state,
            'score': score,
            'score_label': score_label,
            'listing_price': listing_price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'potential_roi': potential_roi,
            'listing_url': property_data.get('listing_url', '#'),
            'sender_name': property_data.get('sender_name', 'Investment Team'),
            'subject': subject
        }

        # Render templates
        html_body = html_template.render(**context)
        plain_body = plain_template.render(**context)

        logger.info(f"Rendered email template for: {address}")

        return {
            'html': html_body,
            'plain': plain_body,
            'subject': subject
        }

    @staticmethod
    def render_follow_up_email(property_data: Dict[str, Any], days_since: int) -> Dict[str, str]:
        """
        Render follow-up email for a property

        Args:
            property_data: Property information
            days_since: Days since last email

        Returns:
            Dictionary with 'html', 'plain', 'subject'
        """
        address = property_data.get('address', 'Unknown Address')
        score = int(property_data.get('score', 0))

        subject = f"Follow-up: {address} - Still Available"

        html_body = f"""
        <p>Hi there,</p>

        <p>I wanted to follow up on the investment opportunity I shared {days_since} days ago
        for <strong>{address}</strong> (Bird-Dog Score: {score}/100).</p>

        <p>The property is still available, and I wanted to check if you had any questions
        or would like additional information about this opportunity.</p>

        <p>Please let me know if you'd like to discuss further.</p>

        <p>Best regards,<br>Real Estate OS</p>
        """

        plain_body = f"""
        Hi there,

        I wanted to follow up on the investment opportunity I shared {days_since} days ago
        for {address} (Bird-Dog Score: {score}/100).

        The property is still available, and I wanted to check if you had any questions
        or would like additional information about this opportunity.

        Please let me know if you'd like to discuss further.

        Best regards,
        Real Estate OS
        """

        return {
            'html': html_body,
            'plain': plain_body,
            'subject': subject
        }
