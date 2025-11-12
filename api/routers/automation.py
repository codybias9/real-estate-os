"""Automation router for cadence rules, compliance, and workflow automation."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/automation", tags=["automation"])


# ============================================================================
# Enums
# ============================================================================

class CadenceFrequency(str, Enum):
    """Frequency of cadence rule execution."""
    once = "once"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class CadenceAction(str, Enum):
    """Type of action in a cadence."""
    send_email = "send_email"
    send_sms = "send_sms"
    make_call = "make_call"
    create_task = "create_task"
    update_stage = "update_stage"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    approved = "approved"
    blocked = "blocked"
    warning = "warning"


class ConsentStatus(str, Enum):
    """Consent status for communications."""
    explicit_consent = "explicit_consent"
    implied_consent = "implied_consent"
    no_consent = "no_consent"
    opt_out = "opt_out"


# ============================================================================
# Schemas
# ============================================================================

class CadenceStep(BaseModel):
    """Individual step in a cadence sequence."""
    day: int = Field(..., ge=0, description="Day number in sequence (0 = immediate)")
    action: CadenceAction
    template_id: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class CadenceRuleCreate(BaseModel):
    """Request to create a cadence rule."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    trigger: str = Field(..., description="What triggers this cadence (e.g., 'property_added', 'stage_changed')")
    steps: List[CadenceStep] = Field(..., min_items=1)
    enabled: bool = True
    tags: Optional[List[str]] = []


class CadenceRule(BaseModel):
    """Cadence rule response."""
    id: str
    name: str
    description: Optional[str]
    trigger: str
    steps: List[CadenceStep]
    enabled: bool
    tags: List[str]
    execution_count: int = Field(description="Number of times this rule has been executed")
    last_executed: Optional[str]
    created_at: str
    updated_at: str
    created_by: str


class ValidateSendRequest(BaseModel):
    """Request to validate a send before execution."""
    recipient_email: EmailStr
    recipient_phone: Optional[str] = None
    property_id: str
    message_type: str = Field(..., description="email, sms, or call")
    template_id: Optional[str] = None


class ComplianceIssue(BaseModel):
    """Individual compliance issue."""
    code: str
    severity: str  # error, warning, info
    message: str
    details: Optional[Dict[str, Any]] = None


class ValidateSendResponse(BaseModel):
    """Response from compliance validation."""
    status: ComplianceStatus
    allowed: bool
    issues: List[ComplianceIssue] = []
    recommendations: List[str] = []


class DNCCheckRequest(BaseModel):
    """Request to check Do Not Contact list."""
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    property_id: Optional[str] = None


class DNCCheckResponse(BaseModel):
    """Response from DNC check."""
    is_on_dnc_list: bool
    dnc_type: Optional[str] = Field(None, description="federal, state, internal, or None")
    added_date: Optional[str] = None
    reason: Optional[str] = None
    can_contact: bool


class ConsentCheckRequest(BaseModel):
    """Request to check consent status."""
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    property_id: str


class ConsentCheckResponse(BaseModel):
    """Response from consent check."""
    email_consent: ConsentStatus
    sms_consent: ConsentStatus
    phone_consent: ConsentStatus
    last_consent_date: Optional[str]
    consent_method: Optional[str] = Field(None, description="How consent was obtained")
    can_send_email: bool
    can_send_sms: bool
    can_make_call: bool


# ============================================================================
# Mock Data Store
# ============================================================================

CADENCE_RULES: Dict[str, Dict] = {
    "cad_001": {
        "id": "cad_001",
        "name": "New Property Outreach Sequence",
        "description": "7-day email sequence for newly added off-market properties",
        "trigger": "property_added",
        "steps": [
            {
                "day": 0,
                "action": "send_email",
                "template_id": "tpl_001",
                "subject": None,
                "body": None
            },
            {
                "day": 3,
                "action": "send_email",
                "template_id": "tpl_002",
                "subject": None,
                "body": None
            },
            {
                "day": 7,
                "action": "create_task",
                "template_id": None,
                "subject": "Follow up with phone call",
                "body": "Owner has not responded to emails. Time to call."
            }
        ],
        "enabled": True,
        "tags": ["outreach", "email", "new-property"],
        "execution_count": 347,
        "last_executed": "2025-11-12T08:30:00",
        "created_at": "2025-09-01T10:00:00",
        "updated_at": "2025-10-15T14:00:00",
        "created_by": "demo@realestateos.com"
    },
    "cad_002": {
        "id": "cad_002",
        "name": "Qualified Lead Nurture",
        "description": "Nurture sequence for qualified leads in negotiation",
        "trigger": "stage_changed:qualified",
        "steps": [
            {
                "day": 0,
                "action": "send_email",
                "template_id": "tpl_003",
                "subject": None,
                "body": None
            },
            {
                "day": 2,
                "action": "make_call",
                "template_id": None,
                "subject": "Check-in call",
                "body": "Call to answer questions and move forward"
            },
            {
                "day": 5,
                "action": "send_email",
                "template_id": "tpl_002",
                "subject": None,
                "body": None
            }
        ],
        "enabled": True,
        "tags": ["nurture", "qualified", "multi-channel"],
        "execution_count": 89,
        "last_executed": "2025-11-11T16:45:00",
        "created_at": "2025-09-15T11:00:00",
        "updated_at": "2025-11-01T09:00:00",
        "created_by": "demo@realestateos.com"
    },
    "cad_003": {
        "id": "cad_003",
        "name": "Re-engagement Campaign",
        "description": "Re-engage contacts who went cold after 30 days",
        "trigger": "no_response_30_days",
        "steps": [
            {
                "day": 0,
                "action": "send_email",
                "template_id": "tpl_004",
                "subject": "Still interested in your property?",
                "body": None
            },
            {
                "day": 7,
                "action": "update_stage",
                "template_id": None,
                "subject": None,
                "body": "Move to 'closed_lost' if still no response"
            }
        ],
        "enabled": False,
        "tags": ["re-engagement", "cold-leads"],
        "execution_count": 12,
        "last_executed": "2025-10-28T10:00:00",
        "created_at": "2025-10-01T13:00:00",
        "updated_at": "2025-11-05T15:00:00",
        "created_by": "demo@realestateos.com"
    }
}

# Mock DNC list (phone numbers and emails)
DNC_LIST = {
    "+14155551234": {"type": "federal", "added_date": "2024-05-15", "reason": "Consumer request"},
    "noemail@example.com": {"type": "internal", "added_date": "2025-10-01", "reason": "Previous complaint"},
}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/cadence-rules", response_model=List[CadenceRule])
def list_cadence_rules(enabled: Optional[bool] = None):
    """
    List all cadence rules.

    Cadences automate multi-step outreach sequences based on triggers.
    Can filter by enabled status.
    """
    rules = list(CADENCE_RULES.values())

    # Filter by enabled status
    if enabled is not None:
        rules = [r for r in rules if r["enabled"] == enabled]

    return [CadenceRule(**rule) for rule in rules]


@router.post("/cadence-rules", response_model=CadenceRule, status_code=201)
def create_cadence_rule(rule: CadenceRuleCreate):
    """
    Create a new cadence rule.

    Cadences define automated sequences of actions triggered by events.
    Steps are executed on specified days after the trigger.
    """
    # Generate new ID
    new_id = f"cad_{str(len(CADENCE_RULES) + 1).zfill(3)}"

    new_rule = {
        "id": new_id,
        "name": rule.name,
        "description": rule.description,
        "trigger": rule.trigger,
        "steps": [step.dict() for step in rule.steps],
        "enabled": rule.enabled,
        "tags": rule.tags or [],
        "execution_count": 0,
        "last_executed": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    CADENCE_RULES[new_id] = new_rule

    return CadenceRule(**new_rule)


@router.get("/cadence-rules/{rule_id}", response_model=CadenceRule)
def get_cadence_rule(rule_id: str):
    """
    Get details of a specific cadence rule.
    """
    if rule_id not in CADENCE_RULES:
        raise HTTPException(status_code=404, detail="Cadence rule not found")

    return CadenceRule(**CADENCE_RULES[rule_id])


@router.patch("/cadence-rules/{rule_id}", response_model=CadenceRule)
def update_cadence_rule(rule_id: str, update: CadenceRuleCreate):
    """
    Update a cadence rule.

    Can modify name, description, steps, and enabled status.
    """
    if rule_id not in CADENCE_RULES:
        raise HTTPException(status_code=404, detail="Cadence rule not found")

    rule = CADENCE_RULES[rule_id]

    rule["name"] = update.name
    rule["description"] = update.description
    rule["trigger"] = update.trigger
    rule["steps"] = [step.dict() for step in update.steps]
    rule["enabled"] = update.enabled
    rule["tags"] = update.tags or []
    rule["updated_at"] = datetime.now().isoformat()

    return CadenceRule(**rule)


@router.post("/cadence-rules/{rule_id}/toggle")
def toggle_cadence_rule(rule_id: str):
    """
    Toggle a cadence rule on or off.

    Enables or disables the automatic execution of the rule.
    """
    if rule_id not in CADENCE_RULES:
        raise HTTPException(status_code=404, detail="Cadence rule not found")

    rule = CADENCE_RULES[rule_id]
    rule["enabled"] = not rule["enabled"]
    rule["updated_at"] = datetime.now().isoformat()

    return {
        "rule_id": rule_id,
        "enabled": rule["enabled"],
        "message": f"Cadence rule {'enabled' if rule['enabled'] else 'disabled'}"
    }


@router.delete("/cadence-rules/{rule_id}", status_code=204)
def delete_cadence_rule(rule_id: str):
    """
    Delete a cadence rule.

    Removes the rule from the system. Active executions are not affected.
    """
    if rule_id not in CADENCE_RULES:
        raise HTTPException(status_code=404, detail="Cadence rule not found")

    del CADENCE_RULES[rule_id]
    return None


@router.get("/cadence-rules/{rule_id}/executions")
def get_cadence_executions(rule_id: str, limit: int = 50):
    """
    Get execution history for a cadence rule.

    Shows recent times this cadence was triggered and executed.
    """
    if rule_id not in CADENCE_RULES:
        raise HTTPException(status_code=404, detail="Cadence rule not found")

    # Mock execution history
    executions = []
    for i in range(min(limit, 20)):
        executions.append({
            "execution_id": f"exec_{rule_id}_{i+1}",
            "rule_id": rule_id,
            "property_id": f"prop_{random.randint(1, 100):03d}",
            "triggered_at": (datetime.now() - timedelta(days=i)).isoformat(),
            "status": random.choice(["completed", "completed", "completed", "in_progress", "failed"]),
            "steps_completed": random.randint(1, 3),
            "steps_total": 3
        })

    return executions


# ============================================================================
# Compliance Endpoints
# ============================================================================

@router.post("/compliance/validate-send", response_model=ValidateSendResponse)
def validate_send(request: ValidateSendRequest):
    """
    Pre-send compliance validation.

    Checks all compliance rules before sending a communication:
    - DNC list check
    - Consent verification
    - Send frequency limits
    - Time-of-day restrictions
    - State-specific regulations
    """
    issues = []
    recommendations = []

    # Check DNC list
    if request.recipient_email in DNC_LIST:
        dnc_info = DNC_LIST[request.recipient_email]
        issues.append(ComplianceIssue(
            code="DNC_LIST",
            severity="error",
            message=f"Recipient is on {dnc_info['type']} Do Not Contact list",
            details=dnc_info
        ))

    # Check send frequency (mock)
    if random.random() < 0.1:  # 10% chance of frequency warning
        issues.append(ComplianceIssue(
            code="HIGH_FREQUENCY",
            severity="warning",
            message="Recipient has been contacted 3 times in the last 7 days",
            details={"last_contact": (datetime.now() - timedelta(days=1)).isoformat()}
        ))

    # Check time of day (mock - assume 9am-8pm allowed)
    current_hour = datetime.now().hour
    if current_hour < 9 or current_hour > 20:
        issues.append(ComplianceIssue(
            code="TIME_RESTRICTION",
            severity="warning",
            message="Current time is outside allowed contact hours (9am-8pm local time)",
            details={"current_hour": current_hour, "allowed_range": "9-20"}
        ))
        recommendations.append("Schedule send for tomorrow morning between 9am-12pm")

    # Check if SMS without consent
    if request.message_type == "sms" and random.random() < 0.15:
        issues.append(ComplianceIssue(
            code="NO_SMS_CONSENT",
            severity="error",
            message="No explicit consent for SMS communications",
            details={"consent_required": True}
        ))

    # Determine overall status
    error_count = sum(1 for issue in issues if issue.severity == "error")

    if error_count > 0:
        status = ComplianceStatus.blocked
        allowed = False
    elif len(issues) > 0:
        status = ComplianceStatus.warning
        allowed = True
        recommendations.append("Review warnings before sending")
    else:
        status = ComplianceStatus.approved
        allowed = True

    return ValidateSendResponse(
        status=status,
        allowed=allowed,
        issues=issues,
        recommendations=recommendations
    )


@router.post("/compliance/dnc-check", response_model=DNCCheckResponse)
def check_dnc_list(request: DNCCheckRequest):
    """
    Check if contact is on Do Not Contact list.

    Checks federal, state, and internal DNC lists.
    """
    # Check phone number
    if request.phone_number and request.phone_number in DNC_LIST:
        dnc_info = DNC_LIST[request.phone_number]
        return DNCCheckResponse(
            is_on_dnc_list=True,
            dnc_type=dnc_info["type"],
            added_date=dnc_info["added_date"],
            reason=dnc_info["reason"],
            can_contact=False
        )

    # Check email
    if request.email and request.email in DNC_LIST:
        dnc_info = DNC_LIST[request.email]
        return DNCCheckResponse(
            is_on_dnc_list=True,
            dnc_type=dnc_info["type"],
            added_date=dnc_info["added_date"],
            reason=dnc_info["reason"],
            can_contact=False
        )

    # Not on DNC list
    return DNCCheckResponse(
        is_on_dnc_list=False,
        dnc_type=None,
        added_date=None,
        reason=None,
        can_contact=True
    )


@router.post("/compliance/consent-status", response_model=ConsentCheckResponse)
def check_consent_status(request: ConsentCheckRequest):
    """
    Check consent status for various communication types.

    Returns consent status for email, SMS, and phone communications.
    """
    # Mock consent check
    # In real system, would query consent database

    # Random consent levels for demo
    has_email_consent = random.choice([True, True, True, False])  # 75% have consent
    has_sms_consent = random.choice([True, True, False, False])  # 50% have consent
    has_phone_consent = random.choice([True, True, True, False])  # 75% have consent

    if has_email_consent:
        email_status = ConsentStatus.explicit_consent
    else:
        email_status = ConsentStatus.implied_consent

    if has_sms_consent:
        sms_status = ConsentStatus.explicit_consent
    else:
        sms_status = ConsentStatus.no_consent

    if has_phone_consent:
        phone_status = ConsentStatus.implied_consent
    else:
        phone_status = ConsentStatus.no_consent

    return ConsentCheckResponse(
        email_consent=email_status,
        sms_consent=sms_status,
        phone_consent=phone_status,
        last_consent_date=(datetime.now() - timedelta(days=random.randint(30, 365))).isoformat() if has_email_consent else None,
        consent_method="web_form" if has_email_consent else None,
        can_send_email=email_status != ConsentStatus.opt_out,
        can_send_sms=sms_status == ConsentStatus.explicit_consent,
        can_make_call=phone_status != ConsentStatus.opt_out
    )


@router.post("/compliance/add-to-dnc")
def add_to_dnc(
    phone_number: Optional[str] = None,
    email: Optional[EmailStr] = None,
    reason: str = "User request"
):
    """
    Add a contact to the internal Do Not Contact list.

    Used when a contact requests to opt-out or after a complaint.
    """
    if not phone_number and not email:
        raise HTTPException(status_code=400, detail="Must provide phone_number or email")

    identifier = phone_number or email

    DNC_LIST[identifier] = {
        "type": "internal",
        "added_date": datetime.now().isoformat(),
        "reason": reason
    }

    return {
        "success": True,
        "message": f"Added {identifier} to Do Not Contact list",
        "added_date": DNC_LIST[identifier]["added_date"]
    }


@router.delete("/compliance/remove-from-dnc")
def remove_from_dnc(phone_number: Optional[str] = None, email: Optional[EmailStr] = None):
    """
    Remove a contact from the internal DNC list.

    Cannot remove from federal/state DNC lists - only internal list.
    """
    if not phone_number and not email:
        raise HTTPException(status_code=400, detail="Must provide phone_number or email")

    identifier = phone_number or email

    if identifier in DNC_LIST:
        if DNC_LIST[identifier]["type"] in ["federal", "state"]:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot remove from {DNC_LIST[identifier]['type']} DNC list"
            )

        del DNC_LIST[identifier]
        return {
            "success": True,
            "message": f"Removed {identifier} from Do Not Contact list"
        }

    return {
        "success": True,
        "message": f"{identifier} was not on the internal DNC list"
    }


@router.get("/compliance/stats")
def get_compliance_stats():
    """
    Get compliance statistics and metrics.

    Shows DNC list size, consent rates, and compliance check results.
    """
    return {
        "dnc_list_size": len(DNC_LIST),
        "dnc_by_type": {
            "federal": sum(1 for v in DNC_LIST.values() if v["type"] == "federal"),
            "state": sum(1 for v in DNC_LIST.values() if v["type"] == "state"),
            "internal": sum(1 for v in DNC_LIST.values() if v["type"] == "internal")
        },
        "validation_checks_24h": random.randint(500, 2000),
        "blocked_sends_24h": random.randint(10, 50),
        "warning_sends_24h": random.randint(50, 150),
        "consent_rate_email": round(random.uniform(0.75, 0.95), 2),
        "consent_rate_sms": round(random.uniform(0.40, 0.60), 2),
        "consent_rate_phone": round(random.uniform(0.65, 0.85), 2)
    }
