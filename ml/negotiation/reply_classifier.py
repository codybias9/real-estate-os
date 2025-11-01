"""Reply Classifier
NLP-based classification of seller/owner replies

Classifications:
- interested: Positive response, wants to discuss
- not_interested: Explicit rejection
- counter_offer: Price negotiation
- request_info: Asking for more details
- callback_later: Postponed decision
- auto_reply: Out of office, vacation
- irrelevant: Spam, wrong number
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReplyIntent(Enum):
    """Reply intent classifications"""
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    COUNTER_OFFER = "counter_offer"
    REQUEST_INFO = "request_info"
    CALLBACK_LATER = "callback_later"
    AUTO_REPLY = "auto_reply"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result from reply classification"""
    intent: ReplyIntent
    confidence: float  # 0-1
    matched_patterns: List[str]
    extracted_entities: Dict[str, any]
    sentiment: str  # positive, negative, neutral
    urgency: str  # high, medium, low
    next_action: str  # Recommended next step


class ReplyClassifier:
    """Classify seller replies using rule-based NLP + simple ML"""

    # Keyword patterns for each intent
    INTERESTED_PATTERNS = [
        r'\b(yes|sure|ok|okay|interested|tell me more|sounds good|let\'?s talk)\b',
        r'\b(i\'?m open|willing to discuss|would consider|might be)\b',
        r'\b(call me|give me a call|reach out|get back to)\b',
        r'\b(send (me )?(the|your)|email me)\b',
    ]

    NOT_INTERESTED_PATTERNS = [
        r'\b(no thanks?|not interested|don\'?t contact|stop|remove|unsubscribe)\b',
        r'\b(already sold|under contract|off (the )?market)\b',
        r'\b(not selling|keep(ing)? (the|my) (house|property))\b',
        r'\b(too low|lowball|ridiculous|insult)\b',
    ]

    COUNTER_OFFER_PATTERNS = [
        r'\$\d+[,\d]*',  # Dollar amounts
        r'\b\d+k\b',  # "250k"
        r'\b(what\'?s your best|highest offer|can you do)\b',
        r'\b(my price is|asking|need at least|won\'?t accept less)\b',
        r'\b(counter|negotiate|meet in the middle)\b',
    ]

    REQUEST_INFO_PATTERNS = [
        r'\b(what|how|when|where|why|who)\b',
        r'\b(tell me (more )?about|curious about|want to know)\b',
        r'\b(can you (send|provide|share)|do you have)\b',
        r'\b(more (info|information|details)|explain)\b',
    ]

    CALLBACK_LATER_PATTERNS = [
        r'\b(call back|try again|reach out) (later|next week|in a few)\b',
        r'\b(not (a )?good time|busy|traveling|out of town)\b',
        r'\b(thinking about it|need (to|some) time|let me think)\b',
        r'\b(talk to (my )?(spouse|partner|wife|husband))\b',
    ]

    AUTO_REPLY_PATTERNS = [
        r'\b(out of (the )?office|on vacation|automatic reply|auto.?response)\b',
        r'\b(do not reply|this (is|email) (is )?not monitored)\b',
        r'\b(will (be )?return|back on)\b',
    ]

    def __init__(self):
        # Compile patterns
        self.interested_regex = [re.compile(p, re.IGNORECASE) for p in self.INTERESTED_PATTERNS]
        self.not_interested_regex = [re.compile(p, re.IGNORECASE) for p in self.NOT_INTERESTED_PATTERNS]
        self.counter_offer_regex = [re.compile(p, re.IGNORECASE) for p in self.COUNTER_OFFER_PATTERNS]
        self.request_info_regex = [re.compile(p, re.IGNORECASE) for p in self.REQUEST_INFO_PATTERNS]
        self.callback_later_regex = [re.compile(p, re.IGNORECASE) for p in self.CALLBACK_LATER_PATTERNS]
        self.auto_reply_regex = [re.compile(p, re.IGNORECASE) for p in self.AUTO_REPLY_PATTERNS]

    def classify(self, message: str, context: Optional[Dict] = None) -> ClassificationResult:
        """Classify reply intent

        Args:
            message: Reply text
            context: Optional context (previous messages, property info)

        Returns:
            ClassificationResult
        """

        message_lower = message.lower().strip()

        # Check for auto-reply first
        if self._matches_patterns(message_lower, self.auto_reply_regex):
            return ClassificationResult(
                intent=ReplyIntent.AUTO_REPLY,
                confidence=0.95,
                matched_patterns=["auto_reply"],
                extracted_entities={},
                sentiment="neutral",
                urgency="low",
                next_action="wait_24h"
            )

        # Check for explicit rejection
        not_interested_matches = self._get_matching_patterns(message_lower, self.not_interested_regex)
        if not_interested_matches:
            return ClassificationResult(
                intent=ReplyIntent.NOT_INTERESTED,
                confidence=0.90,
                matched_patterns=not_interested_matches,
                extracted_entities={},
                sentiment="negative",
                urgency="low",
                next_action="archive"
            )

        # Check for counter offer
        counter_matches = self._get_matching_patterns(message_lower, self.counter_offer_regex)
        extracted_price = self._extract_price(message)
        if counter_matches or extracted_price:
            return ClassificationResult(
                intent=ReplyIntent.COUNTER_OFFER,
                confidence=0.85,
                matched_patterns=counter_matches,
                extracted_entities={"price": extracted_price} if extracted_price else {},
                sentiment="neutral",
                urgency="high",
                next_action="evaluate_counter"
            )

        # Check for callback later
        callback_matches = self._get_matching_patterns(message_lower, self.callback_later_regex)
        if callback_matches:
            return ClassificationResult(
                intent=ReplyIntent.CALLBACK_LATER,
                confidence=0.80,
                matched_patterns=callback_matches,
                extracted_entities={},
                sentiment="neutral",
                urgency="medium",
                next_action="schedule_followup"
            )

        # Check for information request
        info_matches = self._get_matching_patterns(message_lower, self.request_info_regex)
        if info_matches:
            return ClassificationResult(
                intent=ReplyIntent.REQUEST_INFO,
                confidence=0.75,
                matched_patterns=info_matches,
                extracted_entities={},
                sentiment="positive",
                urgency="high",
                next_action="send_info"
            )

        # Check for interest
        interest_matches = self._get_matching_patterns(message_lower, self.interested_regex)
        if interest_matches:
            return ClassificationResult(
                intent=ReplyIntent.INTERESTED,
                confidence=0.85,
                matched_patterns=interest_matches,
                extracted_entities={},
                sentiment="positive",
                urgency="high",
                next_action="schedule_call"
            )

        # Check length and content to filter spam
        if len(message) < 10 or self._is_spam(message):
            return ClassificationResult(
                intent=ReplyIntent.IRRELEVANT,
                confidence=0.70,
                matched_patterns=["short_message"],
                extracted_entities={},
                sentiment="neutral",
                urgency="low",
                next_action="ignore"
            )

        # Unknown intent
        return ClassificationResult(
            intent=ReplyIntent.UNKNOWN,
            confidence=0.50,
            matched_patterns=[],
            extracted_entities={},
            sentiment=self._analyze_sentiment(message),
            urgency="medium",
            next_action="manual_review"
        )

    def _matches_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any pattern"""
        return any(p.search(text) for p in patterns)

    def _get_matching_patterns(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """Get list of matched pattern strings"""
        matches = []
        for p in patterns:
            if p.search(text):
                matches.append(p.pattern[:50])  # Truncate pattern
        return matches

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract dollar amount from text"""

        # Match $XXX,XXX or XXXk format
        dollar_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if dollar_match:
            price_str = dollar_match.group(1).replace(',', '')
            return float(price_str)

        # Match XXXk format
        k_match = re.search(r'(\d+)k\b', text, re.IGNORECASE)
        if k_match:
            return float(k_match.group(1)) * 1000

        return None

    def _is_spam(self, text: str) -> bool:
        """Simple spam detection"""

        spam_indicators = [
            r'https?://',  # URLs (often spam)
            r'\b(viagra|cialis|casino|lottery|prize)\b',
            r'\b(click here|act now|limited time)\b',
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in spam_indicators)

    def _analyze_sentiment(self, text: str) -> str:
        """Simple rule-based sentiment analysis"""

        positive_words = ['yes', 'great', 'good', 'interested', 'happy', 'sounds good', 'sure', 'ok']
        negative_words = ['no', 'not', 'don\'t', 'never', 'stop', 'spam', 'bad', 'terrible']

        text_lower = text.lower()

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"

    def batch_classify(self, messages: List[Tuple[str, Dict]]) -> List[ClassificationResult]:
        """Classify multiple messages

        Args:
            messages: List of (message_text, context) tuples

        Returns:
            List of ClassificationResult
        """

        results = []

        for message, context in messages:
            result = self.classify(message, context)
            results.append(result)

        logger.info(f"Classified {len(results)} messages")

        return results


# ============================================================================
# Conversation State Tracking
# ============================================================================

@dataclass
class ConversationState:
    """Track conversation state with a lead"""
    lead_id: str
    property_id: str

    # History
    messages_sent: int = 0
    replies_received: int = 0
    last_sent_at: Optional[datetime] = None
    last_reply_at: Optional[datetime] = None

    # Current state
    current_intent: ReplyIntent = ReplyIntent.UNKNOWN
    interest_score: float = 0.0  # 0-1, tracks engagement

    # Flags
    opted_out: bool = False
    callback_scheduled: bool = False
    deal_in_progress: bool = False


class ConversationTracker:
    """Track conversation states across leads"""

    def __init__(self):
        self.conversations: Dict[str, ConversationState] = {}

    def update_state(
        self,
        lead_id: str,
        property_id: str,
        classification: ClassificationResult
    ) -> ConversationState:
        """Update conversation state based on new classification

        Args:
            lead_id: Lead identifier
            property_id: Property identifier
            classification: Classification result

        Returns:
            Updated ConversationState
        """

        # Get or create conversation state
        key = f"{lead_id}_{property_id}"
        if key not in self.conversations:
            self.conversations[key] = ConversationState(
                lead_id=lead_id,
                property_id=property_id
            )

        state = self.conversations[key]

        # Update based on intent
        state.current_intent = classification.intent
        state.replies_received += 1
        state.last_reply_at = datetime.now()

        # Update interest score
        if classification.intent in [ReplyIntent.INTERESTED, ReplyIntent.REQUEST_INFO]:
            state.interest_score = min(1.0, state.interest_score + 0.3)
        elif classification.intent == ReplyIntent.COUNTER_OFFER:
            state.interest_score = min(1.0, state.interest_score + 0.4)
        elif classification.intent == ReplyIntent.NOT_INTERESTED:
            state.interest_score = 0.0
            state.opted_out = True
        elif classification.intent == ReplyIntent.CALLBACK_LATER:
            state.callback_scheduled = True

        logger.info(f"Updated state for {key}: intent={classification.intent.value}, score={state.interest_score:.2f}")

        return state

    def should_continue_outreach(self, lead_id: str, property_id: str) -> Tuple[bool, str]:
        """Determine if outreach should continue

        Args:
            lead_id: Lead identifier
            property_id: Property identifier

        Returns:
            Tuple of (should_continue, reason)
        """

        key = f"{lead_id}_{property_id}"
        if key not in self.conversations:
            return True, "new_conversation"

        state = self.conversations[key]

        # Check opt-out
        if state.opted_out:
            return False, "opted_out"

        # Check if deal in progress
        if state.deal_in_progress:
            return False, "deal_in_progress"

        # Check message limits
        if state.messages_sent >= 5 and state.replies_received == 0:
            return False, "max_attempts_no_response"

        # Check interest score
        if state.interest_score > 0.5:
            return True, "high_interest"

        if state.interest_score < 0.1 and state.messages_sent >= 3:
            return False, "low_interest"

        return True, "continue"

    def get_state(self, lead_id: str, property_id: str) -> Optional[ConversationState]:
        """Get conversation state

        Args:
            lead_id: Lead identifier
            property_id: Property identifier

        Returns:
            ConversationState if exists, else None
        """

        key = f"{lead_id}_{property_id}"
        return self.conversations.get(key)
