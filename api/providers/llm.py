"""
LLM Provider Implementations

DeterministicTemplateProvider: Template-based generation for development (deterministic)
OpenAIProvider: Real OpenAI API for production
AnthropicProvider: Claude API for production
"""
import logging
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime

from api.config import get_config

logger = logging.getLogger(__name__)


class LlmProvider(ABC):
    """Abstract LLM provider interface"""

    @abstractmethod
    def generate_memo(
        self,
        property_data: Dict,
        template_name: str = "default",
        max_tokens: int = 500
    ) -> str:
        """Generate property memo"""
        pass

    @abstractmethod
    def generate_email_reply(
        self,
        email_context: Dict,
        tone: str = "professional",
        max_tokens: int = 300
    ) -> str:
        """Generate email reply draft"""
        pass

    @abstractmethod
    def generate_objection_response(
        self,
        objection_type: str,
        property_data: Dict,
        max_tokens: int = 200
    ) -> str:
        """Generate objection handling response"""
        pass


class DeterministicTemplateProvider(LlmProvider):
    """
    Deterministic template-based LLM provider for development

    Features:
    - No API calls or costs
    - Same input → same output (deterministic)
    - Stable hashes for snapshot testing
    - Fast generation (<10ms)
    - Works offline
    """

    def __init__(self):
        self.config = get_config()
        logger.info("DeterministicTemplateProvider initialized")

    def _deterministic_hash(self, data: Dict) -> str:
        """Generate deterministic hash from data for consistent output"""
        # Sort keys to ensure consistent ordering
        sorted_json = json.dumps(data, sort_keys=True)
        return hashlib.sha256(sorted_json.encode()).hexdigest()[:8]

    def generate_memo(
        self,
        property_data: Dict,
        template_name: str = "default",
        max_tokens: int = 500
    ) -> str:
        """
        Generate property memo using deterministic templates

        Args:
            property_data: Dict with address, arv, repair_estimate, etc.
            template_name: Template to use (default, detailed, brief)
            max_tokens: Max tokens (ignored for deterministic output)

        Returns:
            Memo text (deterministic based on input)
        """
        # Extract key fields with safe defaults
        address = property_data.get("address", "Property Address")
        city = property_data.get("city", "City")
        state = property_data.get("state", "ST")
        zip_code = property_data.get("zip", "00000")

        arv = property_data.get("arv")
        assessed_value = property_data.get("assessed_value")
        repair_estimate = property_data.get("repair_estimate")
        bird_dog_score = property_data.get("bird_dog_score", 0.5)
        stage = property_data.get("stage", "lead")

        # Generate deterministic hash for stable output
        hash_suffix = self._deterministic_hash(property_data)

        # Format currency values
        arv_str = f"${arv:,.0f}" if arv else "TBD"
        assessed_str = f"${assessed_value:,.0f}" if assessed_value else "TBD"
        repair_str = f"${repair_estimate:,.0f}" if repair_estimate else "Minimal"

        # Calculate potential offer (70% ARV minus repairs)
        if arv and repair_estimate:
            potential_offer = (arv * 0.70) - repair_estimate
            offer_str = f"${potential_offer:,.0f}"
        else:
            offer_str = "TBD pending valuation"

        # Determine investment quality based on bird_dog_score
        if bird_dog_score >= 0.8:
            quality = "excellent"
            recommendation = "STRONG BUY - High confidence investment opportunity"
        elif bird_dog_score >= 0.6:
            quality = "good"
            recommendation = "BUY - Solid investment with good fundamentals"
        elif bird_dog_score >= 0.4:
            quality = "moderate"
            recommendation = "CONSIDER - Requires additional due diligence"
        else:
            quality = "low"
            recommendation = "PASS - Better opportunities available"

        # Generate memo based on template
        if template_name == "brief":
            memo = f"""Investment Memo - {address}

Location: {city}, {state} {zip_code}
Score: {bird_dog_score:.1%} ({quality})
ARV: {arv_str} | Repairs: {repair_str}
Offer Range: {offer_str}

{recommendation}

Ref: {hash_suffix}"""

        elif template_name == "detailed":
            memo = f"""INVESTMENT ANALYSIS MEMO

Property: {address}
Location: {city}, {state} {zip_code}
Current Stage: {stage.upper()}

FINANCIAL OVERVIEW
─────────────────
After Repair Value (ARV): {arv_str}
Current Assessed Value: {assessed_str}
Estimated Repairs: {repair_str}
Potential Offer: {offer_str}

INVESTMENT METRICS
─────────────────
Bird Dog Score: {bird_dog_score:.1%}
Investment Quality: {quality.upper()}
Confidence Level: {"High" if bird_dog_score >= 0.7 else "Medium" if bird_dog_score >= 0.5 else "Low"}

RECOMMENDATION
─────────────────
{recommendation}

This analysis uses deterministic templates based on property fundamentals.
For AI-enhanced insights, enable production mode with real LLM provider.

Analysis ID: {hash_suffix}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"""

        else:  # default template
            memo = f"""Investment Memo: {address}

PROPERTY OVERVIEW
{address}
{city}, {state} {zip_code}

VALUATION
After Repair Value: {arv_str}
Assessed Value: {assessed_str}
Repair Estimate: {repair_str}

ANALYSIS
Bird Dog Score: {bird_dog_score:.1%} - {quality.upper()} quality
Current Stage: {stage}

RECOMMENDATION
{recommendation}

Initial offer range: {offer_str}
This represents approximately 70% ARV minus estimated repairs,
following standard wholesale/flip investment formula.

NEXT STEPS
1. Verify ARV with recent comps
2. Schedule property walkthrough for repair validation
3. Pull title report and lien search
4. Contact seller to discuss timeline and motivation

Reference: {hash_suffix}
Generated: {datetime.utcnow().strftime('%Y-%m-%d')}"""

        return memo

    def generate_email_reply(
        self,
        email_context: Dict,
        tone: str = "professional",
        max_tokens: int = 300
    ) -> str:
        """
        Generate email reply draft using deterministic templates

        Args:
            email_context: Dict with from_email, subject, body, property_id
            tone: Email tone (professional, casual, urgent)
            max_tokens: Max tokens (ignored)

        Returns:
            Email reply text
        """
        sender = email_context.get("from_email", "the property owner")
        subject = email_context.get("subject", "")
        original_body = email_context.get("body", "")
        property_address = email_context.get("property_address", "your property")

        # Determine reply type from context
        body_lower = original_body.lower()

        if "not interested" in body_lower or "no thank" in body_lower:
            reply_type = "not_interested"
        elif "price" in body_lower or "offer" in body_lower or "how much" in body_lower:
            reply_type = "pricing_inquiry"
        elif "more info" in body_lower or "tell me more" in body_lower or "details" in body_lower:
            reply_type = "info_request"
        elif "yes" in body_lower or "interested" in body_lower or "call" in body_lower:
            reply_type = "positive_response"
        else:
            reply_type = "general"

        # Generate reply based on type and tone
        if reply_type == "not_interested":
            if tone == "casual":
                reply = f"""No problem at all! I completely understand.

Just so you know, I keep a list of properties I'm interested in, and I check back every 6-12 months to see if anything has changed. Would it be okay if I followed up with you down the road?

Either way, I appreciate you taking the time to respond. If your situation changes or you know anyone else looking to sell in the area, feel free to reach out anytime.

Best regards"""
            else:
                reply = f"""Thank you for your response. I completely understand and appreciate you letting me know.

If circumstances change in the future, please don't hesitate to reach out. I maintain relationships with property owners long-term and would be happy to discuss opportunities down the road.

I wish you all the best with {property_address}.

Respectfully"""

        elif reply_type == "pricing_inquiry":
            reply = f"""Great question! I'd be happy to discuss numbers with you.

To give you the most accurate offer, I'd like to schedule a brief call or property walkthrough. This helps me understand:
- Current condition and any needed repairs
- Your timeline and goals
- Any specific concerns or constraints

I typically make fair, no-obligation cash offers within 24-48 hours of seeing the property. Many sellers appreciate the speed and certainty compared to traditional listings.

Are you available for a quick 15-minute call this week? I have openings tomorrow afternoon or Thursday morning.

Looking forward to connecting"""

        elif reply_type == "info_request":
            reply = f"""Thanks for your interest! I'd be happy to provide more information.

I'm a local real estate investor focused on {property_address.split(',')[-1].strip() if ',' in property_address else 'the area'}. I buy properties in as-is condition - no repairs needed, no realtor commissions, and we can close on your timeline.

Here's typically how it works:
1. Quick property walkthrough (15-30 minutes)
2. Cash offer within 24-48 hours
3. Flexible closing date (as fast as 7 days or several months out)
4. We handle all paperwork and closing costs

Would you be open to a brief call this week to discuss your situation and see if this approach might work for you?

I'm available tomorrow afternoon or Thursday morning. What works best for you?"""

        elif reply_type == "positive_response":
            reply = f"""Excellent! I'm glad to hear from you.

Let's schedule a time to connect. I'm available:
- Tomorrow afternoon (2-5pm)
- Thursday morning (9am-12pm)
- Friday afternoon (1-4pm)

The call typically takes 10-15 minutes. I'll ask a few questions about the property and your timeline, and then we can schedule a walkthrough if it makes sense for both of us.

What day and time works best for you?

Looking forward to speaking with you!"""

        else:  # general
            reply = f"""Thank you for reaching out about {property_address}.

I'd love to learn more about your situation and see if I can help. Would you be available for a quick call this week?

I typically like to understand:
- Your timeline and goals
- Current property condition
- Any specific concerns or constraints

Based on that conversation, I can usually provide a fair cash offer within 24-48 hours.

I have availability tomorrow afternoon or Thursday morning. Does either of those work for you?

Best regards"""

        return reply

    def generate_objection_response(
        self,
        objection_type: str,
        property_data: Dict,
        max_tokens: int = 200
    ) -> str:
        """
        Generate objection handling response using deterministic templates

        Args:
            objection_type: Type of objection (price_too_low, need_repairs, timing, etc.)
            property_data: Dict with property details
            max_tokens: Max tokens (ignored)

        Returns:
            Objection response text
        """
        objection_responses = {
            "price_too_low": """I understand your concern about the offer price. Let me explain how I arrived at this number:

My offer is based on:
- Current market comps in your area
- Estimated repair costs needed
- My costs (closing, holding, financing)
- A reasonable profit margin for the risk I'm taking

As an investor buying with cash, I have to account for all these factors. However, I'm always open to discussion. If you have recent appraisals or comp data that suggests a higher value, I'd be happy to review them and adjust my offer if warranted.

What price range were you hoping for?""",

            "need_repairs": """Actually, that's one of the main benefits of selling to me - you don't need to make ANY repairs.

I buy properties in as-is condition. That means:
- No fixing, cleaning, or staging required
- No worry about passing inspections
- No last-minute buyer requests for repairs
- Close in current condition

The repair costs are already factored into my offer, so you can walk away without spending a dime on improvements. This saves you time, money, and stress.

Does that help address your concern?""",

            "timing": """I completely understand - timing is crucial, and I want to work around YOUR schedule, not mine.

I can be flexible with closing:
- Need to close fast? We can do 7-10 days
- Need more time? We can close in 30, 60, even 90+ days
- Need to stay temporarily after closing? We can arrange a rent-back

My goal is to make this as convenient as possible for you. What timeline works best for your situation?""",

            "trust_concerns": """That's a very smart concern, and I appreciate you being cautious. There are unfortunately some bad actors in real estate investing.

Here's how I operate:
- All offers in writing with clear terms
- Recommended you have an attorney review everything
- References from past sellers available on request
- Licensed and insured with verifiable track record
- Close through reputable local title company

I never ask for any money upfront, and you're not obligated until we're at the closing table with the title company. You should absolutely verify everything I'm telling you.

Would it help if I provided references from sellers I've worked with in the past?""",

            "family_consulting": """Absolutely! This is a major decision and you should definitely consult with family, advisors, or anyone else you trust.

I encourage you to:
- Show them my offer letter
- Have them review all terms and conditions
- Get their input on the timeline
- Consult with an attorney or CPA if needed

There's no pressure or rush from my end. Take whatever time you need to feel comfortable. If you have questions after discussing with others, I'm always available.

How much time do you think you'll need to review with your family?""",

            "market_waiting": """I understand the temptation to wait for the market. Let me share some things to consider:

Waiting for a better market means:
- Continued property taxes, insurance, utilities
- Ongoing maintenance and upkeep costs
- Risk of property damage or code violations
- Market timing is very difficult - even experts get it wrong

Benefits of selling now:
- Immediate cash with certainty
- No ongoing carrying costs
- No risk of market downturn
- Money can be invested elsewhere

That said, if you truly believe waiting is best, I respect that. I just want to make sure you're considering all factors. Would you like to discuss the specific numbers?"""
        }

        return objection_responses.get(
            objection_type,
            "I understand your concern. Can you tell me more about what's important to you in this situation? I want to make sure I'm addressing your specific needs and concerns."
        )


class OpenAIProvider(LlmProvider):
    """
    OpenAI LLM provider for production

    Uses GPT-4 or GPT-3.5-turbo for content generation
    """

    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.OPENAI_API_KEY
        self.model = "gpt-4-turbo-preview"  # or gpt-3.5-turbo for cost savings

        if not self.api_key:
            logger.warning("OpenAIProvider initialized without API key")
        else:
            logger.info(f"OpenAIProvider initialized with model: {self.model}")

    def generate_memo(
        self,
        property_data: Dict,
        template_name: str = "default",
        max_tokens: int = 500
    ) -> str:
        """Generate property memo using OpenAI"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # Build prompt
            prompt = f"""Generate a professional investment memo for this property:

Address: {property_data.get('address', 'N/A')}
City: {property_data.get('city', 'N/A')}
State: {property_data.get('state', 'N/A')}
ARV: ${property_data.get('arv', 0):,.0f}
Assessed Value: ${property_data.get('assessed_value', 0):,.0f}
Repair Estimate: ${property_data.get('repair_estimate', 0):,.0f}
Bird Dog Score: {property_data.get('bird_dog_score', 0):.1%}
Stage: {property_data.get('stage', 'lead')}

Format: {template_name}
Focus on investment potential, risks, and recommended offer strategy."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a real estate investment analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            memo = response.choices[0].message.content
            logger.info(f"Generated memo via OpenAI ({len(memo)} chars)")
            return memo

        except ImportError:
            raise Exception("OpenAI package not installed - install with 'pip install openai'")
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise Exception(f"LLM generation failed: {e}")

    def generate_email_reply(
        self,
        email_context: Dict,
        tone: str = "professional",
        max_tokens: int = 300
    ) -> str:
        """Generate email reply using OpenAI"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            prompt = f"""Draft a reply to this email from a property seller:

From: {email_context.get('from_email', 'Unknown')}
Subject: {email_context.get('subject', 'No subject')}
Body: {email_context.get('body', '')}

Property: {email_context.get('property_address', 'N/A')}
Tone: {tone}

Reply should be helpful, professional, and move the conversation forward."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional real estate investor responding to sellers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.8
            )

            reply = response.choices[0].message.content
            logger.info(f"Generated email reply via OpenAI ({len(reply)} chars)")
            return reply

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise Exception(f"LLM generation failed: {e}")

    def generate_objection_response(
        self,
        objection_type: str,
        property_data: Dict,
        max_tokens: int = 200
    ) -> str:
        """Generate objection response using OpenAI"""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            prompt = f"""Generate a response to this seller objection:

Objection Type: {objection_type}
Property: {property_data.get('address', 'N/A')}
ARV: ${property_data.get('arv', 0):,.0f}
Offer: ${property_data.get('offer_amount', 0):,.0f}

Respond professionally, address concerns, and keep conversation moving forward."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skilled real estate negotiator handling seller objections."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            objection_response = response.choices[0].message.content
            logger.info(f"Generated objection response via OpenAI ({len(objection_response)} chars)")
            return objection_response

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise Exception(f"LLM generation failed: {e}")


class AnthropicProvider(LlmProvider):
    """
    Anthropic Claude provider for production

    Uses Claude 3 for content generation
    """

    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.ANTHROPIC_API_KEY
        self.model = "claude-3-sonnet-20240229"

        if not self.api_key:
            logger.warning("AnthropicProvider initialized without API key")
        else:
            logger.info(f"AnthropicProvider initialized with model: {self.model}")

    def generate_memo(
        self,
        property_data: Dict,
        template_name: str = "default",
        max_tokens: int = 500
    ) -> str:
        """Generate property memo using Claude"""
        if not self.api_key:
            raise Exception("Anthropic API key not configured")

        # Implementation similar to OpenAI but using Anthropic SDK
        logger.warning("AnthropicProvider.generate_memo not fully implemented")
        return "Claude-based memo generation pending full implementation"

    def generate_email_reply(
        self,
        email_context: Dict,
        tone: str = "professional",
        max_tokens: int = 300
    ) -> str:
        """Generate email reply using Claude"""
        if not self.api_key:
            raise Exception("Anthropic API key not configured")

        logger.warning("AnthropicProvider.generate_email_reply not fully implemented")
        return "Claude-based reply generation pending full implementation"

    def generate_objection_response(
        self,
        objection_type: str,
        property_data: Dict,
        max_tokens: int = 200
    ) -> str:
        """Generate objection response using Claude"""
        if not self.api_key:
            raise Exception("Anthropic API key not configured")

        logger.warning("AnthropicProvider.generate_objection_response not fully implemented")
        return "Claude-based objection response pending full implementation"
