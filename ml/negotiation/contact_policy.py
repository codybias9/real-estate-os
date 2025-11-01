"""Contact Policy Engine
Enforces contact rules, compliance, and best practices

Rules:
- Quiet hours (no contact 9 PM - 8 AM local time)
- Frequency caps (max 1 contact per 2 days per lead)
- Do-not-contact list (opted out, removed)
- Daily limits (max 100 contacts per day per user)
- TCPA compliance for calls/SMS
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
import pytz
import logging

logger = logging.getLogger(__name__)


class ContactChannel(Enum):
    """Contact channels"""
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"
    DIRECT_MAIL = "direct_mail"


class ContactOutcome(Enum):
    """Contact attempt outcomes"""
    ALLOWED = "allowed"
    BLOCKED_QUIET_HOURS = "blocked_quiet_hours"
    BLOCKED_FREQUENCY_CAP = "blocked_frequency_cap"
    BLOCKED_DNC = "blocked_dnc"
    BLOCKED_DAILY_LIMIT = "blocked_daily_limit"
    BLOCKED_OPT_OUT = "blocked_opt_out"
    BLOCKED_COMPLIANCE = "blocked_compliance"


@dataclass
class ContactRule:
    """Contact policy rule"""
    rule_name: str
    enabled: bool = True

    # Quiet hours
    quiet_start: time = time(21, 0)  # 9 PM
    quiet_end: time = time(8, 0)  # 8 AM
    respect_timezone: bool = True

    # Frequency caps
    min_hours_between_contacts: int = 48  # 2 days
    max_contacts_per_week: int = 2
    max_contacts_total: int = 5

    # Daily limits
    max_contacts_per_day_per_user: int = 100
    max_contacts_per_day_per_lead: int = 1

    # Channel-specific rules
    sms_opt_in_required: bool = True
    phone_opt_in_required: bool = True

    # Compliance
    check_dnc_registry: bool = True
    honor_opt_outs: bool = True


@dataclass
class ContactAttempt:
    """Contact attempt record"""
    lead_id: str
    channel: ContactChannel
    timestamp: datetime
    outcome: ContactOutcome
    blocked_by: Optional[str] = None


@dataclass
class LeadContactHistory:
    """Contact history for a lead"""
    lead_id: str
    opted_out: bool = False
    opted_out_date: Optional[datetime] = None
    opt_in_sms: bool = False
    opt_in_phone: bool = False

    # Contact history
    attempts: List[ContactAttempt] = field(default_factory=list)
    last_contact_at: Optional[datetime] = None
    total_contacts: int = 0

    # DNC status
    on_dnc_registry: bool = False
    on_internal_dnc: bool = False


class ContactPolicyEngine:
    """Enforce contact policies"""

    def __init__(self, rule: ContactRule):
        self.rule = rule
        self.lead_histories: Dict[str, LeadContactHistory] = {}
        self.daily_contact_counts: Dict[str, Dict[str, int]] = {}  # {date: {user_id: count}}

    def can_contact(
        self,
        lead_id: str,
        channel: ContactChannel,
        user_id: str,
        lead_timezone: str = "America/New_York",
        current_time: Optional[datetime] = None
    ) -> Tuple[ContactOutcome, Optional[str]]:
        """Check if contact is allowed

        Args:
            lead_id: Lead identifier
            channel: Contact channel
            user_id: User making contact
            lead_timezone: Lead's timezone
            current_time: Current time (default: now)

        Returns:
            Tuple of (outcome, reason)
        """

        if current_time is None:
            current_time = datetime.now(pytz.timezone(lead_timezone))

        # Get or create lead history
        if lead_id not in self.lead_histories:
            self.lead_histories[lead_id] = LeadContactHistory(lead_id=lead_id)

        history = self.lead_histories[lead_id]

        # Rule 1: Check opt-out status
        if self.rule.honor_opt_outs and history.opted_out:
            return ContactOutcome.BLOCKED_OPT_OUT, "Lead has opted out"

        # Rule 2: Check DNC registry
        if self.rule.check_dnc_registry:
            if history.on_dnc_registry or history.on_internal_dnc:
                return ContactOutcome.BLOCKED_DNC, "Lead on do-not-contact list"

        # Rule 3: Check channel-specific opt-in requirements
        if channel == ContactChannel.SMS:
            if self.rule.sms_opt_in_required and not history.opt_in_sms:
                return ContactOutcome.BLOCKED_COMPLIANCE, "SMS opt-in required"

        if channel == ContactChannel.PHONE:
            if self.rule.phone_opt_in_required and not history.opt_in_phone:
                return ContactOutcome.BLOCKED_COMPLIANCE, "Phone opt-in required (TCPA)"

        # Rule 4: Check quiet hours
        if self.rule.respect_timezone:
            allowed, reason = self._check_quiet_hours(current_time, lead_timezone)
            if not allowed:
                return ContactOutcome.BLOCKED_QUIET_HOURS, reason

        # Rule 5: Check frequency caps
        allowed, reason = self._check_frequency_caps(history, current_time)
        if not allowed:
            return ContactOutcome.BLOCKED_FREQUENCY_CAP, reason

        # Rule 6: Check daily limits
        allowed, reason = self._check_daily_limits(user_id, lead_id, current_time)
        if not allowed:
            return ContactOutcome.BLOCKED_DAILY_LIMIT, reason

        # All checks passed
        return ContactOutcome.ALLOWED, "Contact allowed"

    def _check_quiet_hours(
        self,
        current_time: datetime,
        timezone: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if current time is within quiet hours

        Args:
            current_time: Current time
            timezone: Timezone string

        Returns:
            Tuple of (allowed, reason)
        """

        # Convert to lead's local time
        tz = pytz.timezone(timezone)
        local_time = current_time.astimezone(tz)

        current_hour_minute = local_time.time()

        # Check if within quiet hours
        # Quiet hours: 9 PM - 8 AM
        if self.rule.quiet_start < self.rule.quiet_end:
            # Normal case: quiet_start=21:00, quiet_end=08:00 doesn't work this way
            # Need to handle overnight range
            pass

        # Handle overnight quiet hours (e.g., 21:00 - 08:00)
        if self.rule.quiet_start > self.rule.quiet_end:
            # Quiet hours span midnight
            if current_hour_minute >= self.rule.quiet_start or current_hour_minute < self.rule.quiet_end:
                return False, f"Quiet hours ({self.rule.quiet_start.strftime('%H:%M')} - {self.rule.quiet_end.strftime('%H:%M')} local)"
        else:
            # Quiet hours within same day
            if self.rule.quiet_start <= current_hour_minute < self.rule.quiet_end:
                return False, f"Quiet hours ({self.rule.quiet_start.strftime('%H:%M')} - {self.rule.quiet_end.strftime('%H:%M')} local)"

        return True, None

    def _check_frequency_caps(
        self,
        history: LeadContactHistory,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check frequency caps

        Args:
            history: Lead contact history
            current_time: Current time

        Returns:
            Tuple of (allowed, reason)
        """

        # Check total contacts limit
        if history.total_contacts >= self.rule.max_contacts_total:
            return False, f"Maximum total contacts reached ({self.rule.max_contacts_total})"

        # Check minimum time between contacts
        if history.last_contact_at:
            hours_since_last = (current_time - history.last_contact_at).total_seconds() / 3600
            if hours_since_last < self.rule.min_hours_between_contacts:
                return False, f"Minimum {self.rule.min_hours_between_contacts}h between contacts (last contact {hours_since_last:.1f}h ago)"

        # Check weekly limit
        week_ago = current_time - timedelta(days=7)
        contacts_last_week = sum(
            1 for attempt in history.attempts
            if attempt.timestamp >= week_ago and attempt.outcome == ContactOutcome.ALLOWED
        )

        if contacts_last_week >= self.rule.max_contacts_per_week:
            return False, f"Maximum {self.rule.max_contacts_per_week} contacts per week reached"

        return True, None

    def _check_daily_limits(
        self,
        user_id: str,
        lead_id: str,
        current_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check daily limits

        Args:
            user_id: User ID
            lead_id: Lead ID
            current_time: Current time

        Returns:
            Tuple of (allowed, reason)
        """

        today = current_time.date().isoformat()

        # Initialize counts for today
        if today not in self.daily_contact_counts:
            self.daily_contact_counts[today] = {}

        if user_id not in self.daily_contact_counts[today]:
            self.daily_contact_counts[today][user_id] = 0

        # Check user's daily limit
        user_count_today = self.daily_contact_counts[today][user_id]
        if user_count_today >= self.rule.max_contacts_per_day_per_user:
            return False, f"Daily limit reached for user ({self.rule.max_contacts_per_day_per_user} per day)"

        # Check lead's daily limit
        if lead_id in self.lead_histories:
            history = self.lead_histories[lead_id]
            contacts_today = sum(
                1 for attempt in history.attempts
                if attempt.timestamp.date() == current_time.date() and attempt.outcome == ContactOutcome.ALLOWED
            )

            if contacts_today >= self.rule.max_contacts_per_day_per_lead:
                return False, f"Maximum {self.rule.max_contacts_per_day_per_lead} contact per day per lead"

        return True, None

    def record_contact_attempt(
        self,
        lead_id: str,
        channel: ContactChannel,
        user_id: str,
        outcome: ContactOutcome,
        blocked_by: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """Record a contact attempt

        Args:
            lead_id: Lead identifier
            channel: Contact channel
            user_id: User making contact
            outcome: Contact outcome
            blocked_by: Rule that blocked contact (if applicable)
            timestamp: Timestamp (default: now)
        """

        if timestamp is None:
            timestamp = datetime.now()

        # Get or create history
        if lead_id not in self.lead_histories:
            self.lead_histories[lead_id] = LeadContactHistory(lead_id=lead_id)

        history = self.lead_histories[lead_id]

        # Create attempt record
        attempt = ContactAttempt(
            lead_id=lead_id,
            channel=channel,
            timestamp=timestamp,
            outcome=outcome,
            blocked_by=blocked_by
        )

        history.attempts.append(attempt)

        # Update if successful
        if outcome == ContactOutcome.ALLOWED:
            history.last_contact_at = timestamp
            history.total_contacts += 1

            # Update daily counts
            today = timestamp.date().isoformat()
            if today not in self.daily_contact_counts:
                self.daily_contact_counts[today] = {}
            if user_id not in self.daily_contact_counts[today]:
                self.daily_contact_counts[today][user_id] = 0

            self.daily_contact_counts[today][user_id] += 1

        logger.info(f"Recorded contact attempt: lead={lead_id}, channel={channel.value}, outcome={outcome.value}")

    def mark_opt_out(self, lead_id: str, timestamp: Optional[datetime] = None):
        """Mark lead as opted out

        Args:
            lead_id: Lead identifier
            timestamp: Opt-out timestamp (default: now)
        """

        if timestamp is None:
            timestamp = datetime.now()

        if lead_id not in self.lead_histories:
            self.lead_histories[lead_id] = LeadContactHistory(lead_id=lead_id)

        history = self.lead_histories[lead_id]
        history.opted_out = True
        history.opted_out_date = timestamp

        logger.warning(f"Lead {lead_id} opted out at {timestamp}")

    def mark_opt_in(self, lead_id: str, channels: List[ContactChannel]):
        """Mark lead as opted in for specific channels

        Args:
            lead_id: Lead identifier
            channels: Channels to opt in
        """

        if lead_id not in self.lead_histories:
            self.lead_histories[lead_id] = LeadContactHistory(lead_id=lead_id)

        history = self.lead_histories[lead_id]

        for channel in channels:
            if channel == ContactChannel.SMS:
                history.opt_in_sms = True
            elif channel == ContactChannel.PHONE:
                history.opt_in_phone = True

        logger.info(f"Lead {lead_id} opted in for {[c.value for c in channels]}")

    def add_to_dnc(self, lead_id: str, internal: bool = True):
        """Add lead to do-not-contact list

        Args:
            lead_id: Lead identifier
            internal: If True, add to internal DNC (else assume external registry)
        """

        if lead_id not in self.lead_histories:
            self.lead_histories[lead_id] = LeadContactHistory(lead_id=lead_id)

        history = self.lead_histories[lead_id]

        if internal:
            history.on_internal_dnc = True
        else:
            history.on_dnc_registry = True

        logger.warning(f"Lead {lead_id} added to {'internal' if internal else 'external'} DNC")

    def get_next_allowed_contact_time(
        self,
        lead_id: str,
        channel: ContactChannel,
        user_id: str,
        timezone: str = "America/New_York"
    ) -> Optional[datetime]:
        """Get next time when contact is allowed

        Args:
            lead_id: Lead identifier
            channel: Contact channel
            user_id: User ID
            timezone: Lead's timezone

        Returns:
            Next allowed contact time, or None if never allowed
        """

        # Check if permanently blocked
        if lead_id in self.lead_histories:
            history = self.lead_histories[lead_id]

            if history.opted_out or history.on_dnc_registry or history.on_internal_dnc:
                return None  # Never allowed

            if history.total_contacts >= self.rule.max_contacts_total:
                return None  # Max contacts reached

        # Calculate next allowed time based on frequency caps
        current_time = datetime.now(pytz.timezone(timezone))

        if lead_id in self.lead_histories and self.lead_histories[lead_id].last_contact_at:
            last_contact = self.lead_histories[lead_id].last_contact_at
            next_allowed = last_contact + timedelta(hours=self.rule.min_hours_between_contacts)

            if next_allowed > current_time:
                # Adjust for quiet hours
                next_allowed = self._adjust_for_quiet_hours(next_allowed, timezone)
                return next_allowed

        # If no restrictions, return next non-quiet time
        return self._adjust_for_quiet_hours(current_time, timezone)

    def _adjust_for_quiet_hours(self, target_time: datetime, timezone: str) -> datetime:
        """Adjust time to avoid quiet hours

        Args:
            target_time: Target time
            timezone: Timezone

        Returns:
            Adjusted time (after quiet hours if necessary)
        """

        tz = pytz.timezone(timezone)
        local_time = target_time.astimezone(tz)

        # If during quiet hours, move to end of quiet hours
        current_hour_minute = local_time.time()

        if self.rule.quiet_start > self.rule.quiet_end:
            # Overnight quiet hours
            if current_hour_minute >= self.rule.quiet_start or current_hour_minute < self.rule.quiet_end:
                # Move to quiet_end time
                adjusted = local_time.replace(
                    hour=self.rule.quiet_end.hour,
                    minute=self.rule.quiet_end.minute,
                    second=0
                )

                # If quiet_end is earlier in day, add a day
                if current_hour_minute >= self.rule.quiet_start:
                    adjusted += timedelta(days=1)

                return adjusted

        return target_time


# ============================================================================
# Convenience Functions
# ============================================================================

def create_default_policy() -> ContactRule:
    """Create default contact policy

    Returns:
        ContactRule with safe defaults
    """

    return ContactRule(
        rule_name="default",
        enabled=True,
        quiet_start=time(21, 0),  # 9 PM
        quiet_end=time(8, 0),  # 8 AM
        respect_timezone=True,
        min_hours_between_contacts=48,
        max_contacts_per_week=2,
        max_contacts_total=5,
        max_contacts_per_day_per_user=100,
        max_contacts_per_day_per_lead=1,
        sms_opt_in_required=True,
        phone_opt_in_required=True,
        check_dnc_registry=True,
        honor_opt_outs=True
    )
