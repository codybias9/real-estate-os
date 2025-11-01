"""
Messaging Template Engine

Wave 3.2 Part 3: Generate professional negotiation communications

This module generates templated messages for various negotiation scenarios:
- Initial offer letters
- Counter-offer responses
- Inspection negotiation
- Price reduction requests
- Closing timeline adjustments

Templates are customized based on:
- Negotiation strategy (aggressive/moderate/cautious)
- Talking points and evidence
- Market context
- Relationship tone (professional/friendly/formal)
"""

from typing import List, Dict, Optional
from datetime import datetime
from ml.models.negotiation_brain import (
    NegotiationRecommendation,
    NegotiationStrategy,
    TalkingPoint
)


class MessageTemplate:
    """Base class for message templates"""

    def __init__(self, tone: str = "professional"):
        """
        Initialize template

        Args:
            tone: Message tone (professional/friendly/formal)
        """
        self.tone = tone

    def _get_greeting(self, recipient_name: Optional[str] = None) -> str:
        """Generate appropriate greeting"""
        if recipient_name:
            if self.tone == "friendly":
                return f"Hi {recipient_name},"
            else:
                return f"Dear {recipient_name},"
        else:
            return "Dear Listing Agent," if self.tone == "formal" else "Hello,"

    def _get_closing(self, sender_name: str) -> str:
        """Generate appropriate closing"""
        if self.tone == "friendly":
            return f"Best regards,\n{sender_name}"
        elif self.tone == "formal":
            return f"Sincerely,\n{sender_name}"
        else:
            return f"Best,\n{sender_name}"


class InitialOfferLetter(MessageTemplate):
    """Generate initial offer letter with justification"""

    def generate(
        self,
        recommendation: NegotiationRecommendation,
        property_address: str,
        buyer_name: str,
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Generate initial offer letter

        Args:
            recommendation: Negotiation recommendation with strategy
            property_address: Full property address
            buyer_name: Buyer's name
            buyer_agent_name: Buyer's agent name
            listing_agent_name: Listing agent name (optional)
            additional_context: Additional buyer-specific context

        Returns:
            Formatted offer letter
        """

        greeting = self._get_greeting(listing_agent_name)

        # Opening paragraph - express interest
        opening = self._generate_opening(
            property_address,
            buyer_name,
            recommendation.strategy
        )

        # Offer details
        offer_section = self._generate_offer_section(recommendation)

        # Justification with talking points
        justification = self._generate_justification(
            recommendation.talking_points,
            recommendation.strategy
        )

        # Deal structure
        terms = self._generate_terms_section(recommendation)

        # Closing with next steps
        closing_section = self._generate_closing_section(
            recommendation.recommended_response_time
        )

        # Additional context if provided
        context_section = ""
        if additional_context:
            context_section = f"\n\n{additional_context}"

        # Signature
        signature = self._get_closing(buyer_agent_name)

        # Combine all sections
        letter = f"""{greeting}

{opening}

{offer_section}

{justification}

{terms}

{closing_section}{context_section}

{signature}
"""
        return letter

    def _generate_opening(
        self,
        address: str,
        buyer_name: str,
        strategy: NegotiationStrategy
    ) -> str:
        """Generate opening paragraph"""

        if strategy == NegotiationStrategy.AGGRESSIVE:
            return f"On behalf of my client, {buyer_name}, I am pleased to submit an offer on the property located at {address}. After thorough market analysis, we believe this property presents an opportunity at the right price point."

        elif strategy == NegotiationStrategy.CAUTIOUS:
            return f"On behalf of my client, {buyer_name}, I am delighted to present a strong offer on the exceptional property at {address}. My client is very excited about this property and is prepared to move forward quickly."

        else:  # MODERATE
            return f"On behalf of my client, {buyer_name}, I am writing to submit a competitive offer on the property at {address}. My client has carefully evaluated the property and is enthusiastic about the opportunity."

    def _generate_offer_section(self, rec: NegotiationRecommendation) -> str:
        """Generate offer amount section"""

        offer = rec.recommended_initial_offer
        listing_price = rec.recommended_max_offer  # Approximate from range

        section = f"**Offer Details:**\n\n"
        section += f"- Purchase Price: ${offer:,.0f}\n"
        section += f"- Earnest Money Deposit: ${rec.deal_structure.earnest_money_percent/100 * offer:,.0f} "
        section += f"({rec.deal_structure.earnest_money_percent}%)\n"
        section += f"- Closing Timeline: {rec.deal_structure.closing_timeline_days} days from acceptance\n"

        if rec.deal_structure.escalation_clause:
            section += f"- Escalation Clause: Included (see attached)\n"

        return section

    def _generate_justification(
        self,
        talking_points: List[TalkingPoint],
        strategy: NegotiationStrategy
    ) -> str:
        """Generate offer justification from talking points"""

        if strategy == NegotiationStrategy.CAUTIOUS:
            # Minimal justification for cautious approach
            return "This offer reflects our client's strong interest and commitment to a smooth transaction."

        section = "**Market Analysis:**\n\n"

        if not talking_points:
            section += "Our offer is based on comprehensive market analysis and represents fair market value.\n"
            return section

        # Use top 3 talking points
        section += "Our offer is supported by the following analysis:\n\n"

        for i, point in enumerate(talking_points[:3], 1):
            if point.category == "leverage_point":
                section += f"{i}. **{point.point}** - {point.evidence}\n\n"
            elif point.category == "market_comparison":
                section += f"{i}. {point.point}. {point.evidence}\n\n"
            elif point.category == "value_justification":
                section += f"{i}. {point.point}, supported by {point.evidence.lower()}\n\n"

        return section

    def _generate_terms_section(self, rec: NegotiationRecommendation) -> str:
        """Generate terms and contingencies section"""

        section = "**Proposed Terms:**\n\n"

        # Contingencies
        if rec.deal_structure.contingencies:
            section += "Contingencies:\n"
            for contingency in rec.deal_structure.contingencies:
                if contingency == "inspection":
                    section += f"- Inspection ({rec.deal_structure.inspection_period_days} day period)\n"
                else:
                    section += f"- {contingency.capitalize()}\n"
            section += "\n"

        # Additional terms
        if rec.deal_structure.appraisal_gap_coverage:
            section += f"- Appraisal Gap Coverage: Up to ${rec.deal_structure.appraisal_gap_coverage:,.0f}\n"

        if rec.deal_structure.seller_concessions_target:
            section += f"- Requested Seller Concessions: ${rec.deal_structure.seller_concessions_target:,.0f}\n"

        return section

    def _generate_closing_section(self, response_time: str) -> str:
        """Generate closing/next steps section"""

        return f"""We are prepared to move forward quickly and would appreciate your response within {response_time}. My client is pre-approved and ready to proceed with earnest money deposit immediately upon acceptance.

Please let me know if you have any questions or would like to discuss the offer further. We look forward to working with you."""


class CounterOfferResponse(MessageTemplate):
    """Generate response to seller's counter-offer"""

    def generate(
        self,
        original_offer: float,
        counter_offer: float,
        response_offer: float,
        strategy: NegotiationStrategy,
        talking_points: List[TalkingPoint],
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        concessions: Optional[List[str]] = None
    ) -> str:
        """
        Generate counter-offer response

        Args:
            original_offer: Buyer's initial offer
            counter_offer: Seller's counter-offer amount
            response_offer: Buyer's response offer amount
            strategy: Negotiation strategy
            talking_points: Supporting talking points
            buyer_agent_name: Buyer's agent name
            listing_agent_name: Listing agent name (optional)
            concessions: Alternative concessions being offered

        Returns:
            Formatted response letter
        """

        greeting = self._get_greeting(listing_agent_name)

        # Thank them for counter
        opening = "Thank you for your prompt response and counter-offer. My client has carefully reviewed the terms and would like to continue negotiations."

        # State response offer
        response_section = self._generate_response_offer_section(
            original_offer,
            counter_offer,
            response_offer,
            strategy
        )

        # Justification if needed
        justification = ""
        if strategy == NegotiationStrategy.AGGRESSIVE and talking_points:
            justification = "\n\n" + self._generate_counter_justification(talking_points)

        # Concessions if any
        concessions_section = ""
        if concessions:
            concessions_section = "\n\n" + self._generate_concessions_section(concessions)

        # Closing
        closing_para = "\n\nWe hope this demonstrates our client's continued strong interest while respecting market realities. We look forward to reaching an agreement."

        signature = self._get_closing(buyer_agent_name)

        letter = f"""{greeting}

{opening}

{response_section}{justification}{concessions_section}{closing_para}

{signature}
"""
        return letter

    def _generate_response_offer_section(
        self,
        original: float,
        counter: float,
        response: float,
        strategy: NegotiationStrategy
    ) -> str:
        """Generate response offer paragraph"""

        original_to_counter = counter - original
        response_increase = response - original
        remaining_gap = counter - response

        section = f"**Counter-Offer Response:**\n\n"
        section += f"- Original Offer: ${original:,.0f}\n"
        section += f"- Your Counter: ${counter:,.0f}\n"
        section += f"- Our Response: ${response:,.0f}\n\n"

        if strategy == NegotiationStrategy.AGGRESSIVE:
            section += f"We have increased our offer by ${response_increase:,.0f}, which represents a significant move toward your position. "
        elif strategy == NegotiationStrategy.MODERATE:
            section += f"We are pleased to increase our offer by ${response_increase:,.0f} to meet you closer to your asking position. "
        else:
            section += f"We are increasing our offer by ${response_increase:,.0f} to demonstrate our strong commitment. "

        return section

    def _generate_counter_justification(self, talking_points: List[TalkingPoint]) -> str:
        """Generate justification for counter response"""

        section = "While we remain enthusiastic about the property, we must stay within market parameters:\n\n"

        for point in talking_points[:2]:
            section += f"- {point.point}\n"

        return section

    def _generate_concessions_section(self, concessions: List[str]) -> str:
        """Generate alternative concessions section"""

        section = "To strengthen our position, we are also prepared to:\n\n"

        for concession in concessions:
            section += f"- {concession}\n"

        return section


class InspectionNegotiationLetter(MessageTemplate):
    """Generate post-inspection negotiation letter"""

    def generate(
        self,
        repair_requests: List[Dict[str, any]],
        total_repair_estimate: float,
        requested_credit: float,
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        property_address: str = ""
    ) -> str:
        """
        Generate inspection negotiation letter

        Args:
            repair_requests: List of repair items with estimates
            total_repair_estimate: Total estimated repair cost
            requested_credit: Amount of credit requested
            buyer_agent_name: Buyer's agent name
            listing_agent_name: Listing agent name
            property_address: Property address

        Returns:
            Formatted inspection negotiation letter
        """

        greeting = self._get_greeting(listing_agent_name)

        opening = f"Following the professional inspection of {property_address}, my client would like to address the following items before closing."

        # Repair items
        repairs_section = self._generate_repairs_section(repair_requests, total_repair_estimate)

        # Request
        request_section = f"""
**Request:**

Based on the inspection findings, we respectfully request a seller credit of ${requested_credit:,.0f} at closing to address these items. This will allow my client to handle the repairs after closing with contractors of their choice.

Alternatively, we are open to discussing having the seller complete these repairs prior to closing with licensed contractors and appropriate permits.
"""

        # Closing
        closing_para = "We remain committed to this transaction and believe this is a fair resolution that allows us to move forward to a successful closing."

        signature = self._get_closing(buyer_agent_name)

        letter = f"""{greeting}

{opening}

{repairs_section}

{request_section}

{closing_para}

{signature}
"""
        return letter

    def _generate_repairs_section(
        self,
        repair_requests: List[Dict[str, any]],
        total_estimate: float
    ) -> str:
        """Generate repair items section"""

        section = "**Inspection Findings:**\n\n"

        # Categorize by severity
        critical = [r for r in repair_requests if r.get('severity') == 'critical']
        major = [r for r in repair_requests if r.get('severity') == 'major']
        minor = [r for r in repair_requests if r.get('severity') == 'minor']

        if critical:
            section += "Critical Items:\n"
            for item in critical:
                section += f"- {item['description']}: ${item['estimate']:,.0f}\n"
            section += "\n"

        if major:
            section += "Major Items:\n"
            for item in major:
                section += f"- {item['description']}: ${item['estimate']:,.0f}\n"
            section += "\n"

        if minor:
            section += "Minor Items:\n"
            for item in minor:
                section += f"- {item['description']}: ${item['estimate']:,.0f}\n"
            section += "\n"

        section += f"**Total Estimated Repair Cost: ${total_estimate:,.0f}**\n"

        return section


class MessageGenerator:
    """
    High-level message generation interface

    Simplifies generation of various negotiation messages
    """

    def __init__(self, tone: str = "professional"):
        """
        Initialize generator

        Args:
            tone: Default message tone (professional/friendly/formal)
        """
        self.tone = tone

    def generate_initial_offer_letter(
        self,
        recommendation: NegotiationRecommendation,
        property_address: str,
        buyer_name: str,
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        additional_context: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
        """Generate initial offer letter"""

        template = InitialOfferLetter(tone=tone or self.tone)
        return template.generate(
            recommendation=recommendation,
            property_address=property_address,
            buyer_name=buyer_name,
            buyer_agent_name=buyer_agent_name,
            listing_agent_name=listing_agent_name,
            additional_context=additional_context
        )

    def generate_counter_response(
        self,
        original_offer: float,
        counter_offer: float,
        response_offer: float,
        strategy: NegotiationStrategy,
        talking_points: List[TalkingPoint],
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        concessions: Optional[List[str]] = None,
        tone: Optional[str] = None
    ) -> str:
        """Generate counter-offer response letter"""

        template = CounterOfferResponse(tone=tone or self.tone)
        return template.generate(
            original_offer=original_offer,
            counter_offer=counter_offer,
            response_offer=response_offer,
            strategy=strategy,
            talking_points=talking_points,
            buyer_agent_name=buyer_agent_name,
            listing_agent_name=listing_agent_name,
            concessions=concessions
        )

    def generate_inspection_negotiation(
        self,
        repair_requests: List[Dict[str, any]],
        total_repair_estimate: float,
        requested_credit: float,
        buyer_agent_name: str,
        listing_agent_name: Optional[str] = None,
        property_address: str = "",
        tone: Optional[str] = None
    ) -> str:
        """Generate inspection negotiation letter"""

        template = InspectionNegotiationLetter(tone=tone or self.tone)
        return template.generate(
            repair_requests=repair_requests,
            total_repair_estimate=total_repair_estimate,
            requested_credit=requested_credit,
            buyer_agent_name=buyer_agent_name,
            listing_agent_name=listing_agent_name,
            property_address=property_address
        )

    def generate_quick_message(
        self,
        message_type: str,
        context: Dict[str, any]
    ) -> str:
        """
        Generate quick templated messages for common scenarios

        Args:
            message_type: Type of message (request_showing, schedule_inspection, etc.)
            context: Context dictionary with required fields for message type

        Returns:
            Formatted message
        """

        if message_type == "request_showing":
            return self._generate_showing_request(context)
        elif message_type == "schedule_inspection":
            return self._generate_inspection_scheduling(context)
        elif message_type == "request_extension":
            return self._generate_extension_request(context)
        elif message_type == "confirm_closing":
            return self._generate_closing_confirmation(context)
        else:
            raise ValueError(f"Unknown message type: {message_type}")

    def _generate_showing_request(self, context: Dict) -> str:
        """Generate showing request message"""
        return f"""Hello,

I have a buyer interested in viewing {context.get('address', 'the property')}. Would {context.get('proposed_times', 'this week')} work for a showing?

My client is pre-approved and actively searching in this price range.

Please let me know available times.

Best,
{context.get('agent_name', 'Buyer\'s Agent')}
"""

    def _generate_inspection_scheduling(self, context: Dict) -> str:
        """Generate inspection scheduling message"""
        return f"""Hello,

We would like to schedule the inspection for {context.get('address', 'the property')} within the {context.get('inspection_period', '10-day')} inspection period.

Proposed inspection date: {context.get('proposed_date', 'TBD')}
Inspector: {context.get('inspector_name', 'To be confirmed')}

Please confirm access and notify if seller will be present.

Best,
{context.get('agent_name', 'Buyer\'s Agent')}
"""

    def _generate_extension_request(self, context: Dict) -> str:
        """Generate contingency extension request"""
        return f"""Hello,

We are requesting a {context.get('extension_days', 'X')}-day extension on the {context.get('contingency_type', 'inspection')} contingency for {context.get('address', 'the property')}.

Reason: {context.get('reason', 'Additional time needed to complete due diligence')}

All other terms remain unchanged. We are committed to the transaction and just need this additional time.

Please confirm acceptance of this extension.

Best,
{context.get('agent_name', 'Buyer\'s Agent')}
"""

    def _generate_closing_confirmation(self, context: Dict) -> str:
        """Generate closing confirmation message"""
        return f"""Hello,

This confirms we are ready to proceed to closing for {context.get('address', 'the property')}.

Closing Details:
- Date: {context.get('closing_date', 'TBD')}
- Time: {context.get('closing_time', 'TBD')}
- Location: {context.get('closing_location', 'TBD')}

My client will be present and is prepared to close. Please confirm these details and let me know if you need anything further.

Looking forward to a smooth closing!

Best,
{context.get('agent_name', 'Buyer\'s Agent')}
"""
