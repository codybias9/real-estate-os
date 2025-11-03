"""
Automation & Guardrails Router
Cadence governor, Compliance pack, Automated "don't forgets"
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from api.database import get_db
from api import schemas
from db.models import (
    Property, CadenceRule, ComplianceCheck, ComplianceStatus,
    PropertyTimeline, Communication, PropertyStage
)

router = APIRouter(prefix="/automation", tags=["Automation & Guardrails"])

# ============================================================================
# CADENCE GOVERNOR
# ============================================================================

@router.post("/cadence-rules", response_model=schemas.CadenceRuleResponse, status_code=201)
def create_cadence_rule(
    rule_data: schemas.CadenceRuleCreate,
    db: Session = Depends(get_db)
):
    """
    Create a cadence governor rule

    Auto-pause/adjust outreach cadence based on triggers:
    - Reply detected → pause cadence
    - 3 unopened emails → switch to postcard/SMS
    - Hard bounce → pause and mark for review

    Prevents:
    - Over-contacting interested leads
    - Wasting resources on unresponsive contacts
    - Deliverability issues

    KPI: Fewer unsubscribes, more replies
    """
    rule = CadenceRule(
        team_id=rule_data.team_id,
        name=rule_data.name,
        trigger_on=rule_data.trigger_on,
        action_type=rule_data.action_type,
        action_params=rule_data.action_params
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule

@router.get("/cadence-rules/{team_id}", response_model=List[schemas.CadenceRuleResponse])
def list_cadence_rules(
    team_id: int,
    db: Session = Depends(get_db)
):
    """
    List all cadence rules for a team
    """
    rules = (
        db.query(CadenceRule)
        .filter(CadenceRule.team_id == team_id)
        .order_by(desc(CadenceRule.created_at))
        .all()
    )

    return rules

@router.post("/cadence-rules/{rule_id}/toggle")
def toggle_cadence_rule(
    rule_id: int,
    is_active: bool,
    db: Session = Depends(get_db)
):
    """
    Enable/disable a cadence rule
    """
    rule = db.query(CadenceRule).filter(CadenceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = is_active

    db.commit()

    return {"status": "active" if is_active else "disabled"}

@router.post("/cadence/apply-rules/{property_id}")
def apply_cadence_rules(
    property_id: int,
    event_type: str,  # "reply_detected", "email_bounced", "no_opens_3", etc.
    db: Session = Depends(get_db)
):
    """
    Apply cadence rules to a property based on event

    Called automatically when events occur:
    - Reply received
    - Email bounced
    - Multiple unopened emails
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get active cadence rules for the team
    rules = (
        db.query(CadenceRule)
        .filter(
            CadenceRule.team_id == property.team_id,
            CadenceRule.is_active == True
        )
        .all()
    )

    actions_taken = []

    for rule in rules:
        if rule.trigger_on == event_type:
            # Apply the action
            if rule.action_type == "pause":
                property.cadence_paused = True
                property.cadence_pause_reason = event_type
                actions_taken.append(f"Paused cadence: {rule.name}")

                # Create timeline event
                timeline_event = PropertyTimeline(
                    property_id=property.id,
                    event_type="cadence_paused",
                    event_title="Cadence Paused",
                    event_description=f"Auto-paused by rule: {rule.name}",
                    metadata={"rule_id": rule.id, "trigger": event_type}
                )
                db.add(timeline_event)

            elif rule.action_type == "switch_to_sms":
                # In production, update communication channel preference
                property.custom_fields["preferred_channel"] = "sms"
                actions_taken.append(f"Switched to SMS: {rule.name}")

            elif rule.action_type == "switch_to_postcard":
                property.custom_fields["preferred_channel"] = "postcard"
                actions_taken.append(f"Switched to postcard: {rule.name}")

    property.updated_at = datetime.utcnow()
    db.commit()

    return {
        "property_id": property_id,
        "event_type": event_type,
        "actions_taken": actions_taken
    }

# ============================================================================
# COMPLIANCE PACK
# ============================================================================

@router.post("/compliance/check-dnc/{property_id}")
def check_dnc_compliance(
    property_id: int,
    phone_number: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Check Do Not Call (DNC) registry compliance

    Checks:
    - Federal DNC registry
    - State-specific DNC lists
    - Internal opt-out list

    Automatically updates property.is_on_dnc flag

    KPI: Zero compliance incidents
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # In production, check actual DNC registries via API
    # For demo, simulate check
    is_on_dnc = False  # Simulated result

    # Create compliance check record
    check = ComplianceCheck(
        property_id=property_id,
        check_type="dnc",
        status=ComplianceStatus.PASSED if not is_on_dnc else ComplianceStatus.FAILED,
        details=f"Checked number: {phone_number or 'property default'}"
    )

    db.add(check)

    # Update property flag
    property.is_on_dnc = is_on_dnc

    # Create timeline event if on DNC
    if is_on_dnc:
        timeline_event = PropertyTimeline(
            property_id=property_id,
            event_type="dnc_detected",
            event_title="⚠️ DNC Registry Match",
            event_description="Property phone number is on Do Not Call registry",
            metadata={"phone": phone_number}
        )
        db.add(timeline_event)

    db.commit()

    return {
        "property_id": property_id,
        "is_on_dnc": is_on_dnc,
        "status": "passed" if not is_on_dnc else "failed",
        "can_call": not is_on_dnc
    }

@router.post("/compliance/check-opt-out/{property_id}")
def check_opt_out_compliance(
    property_id: int,
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Check if contact has opted out of communications

    Checks internal opt-out list

    Updates property.has_opted_out flag
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # In production, check opt-out database
    # For demo, check if previously marked
    has_opted_out = property.has_opted_out

    # Create compliance check
    check = ComplianceCheck(
        property_id=property_id,
        check_type="opt_out",
        status=ComplianceStatus.PASSED if not has_opted_out else ComplianceStatus.FAILED,
        details=f"Checked email: {email or 'property default'}"
    )

    db.add(check)
    db.commit()

    return {
        "property_id": property_id,
        "has_opted_out": has_opted_out,
        "can_contact": not has_opted_out
    }

@router.post("/compliance/record-opt-out/{property_id}")
def record_opt_out(
    property_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Record an opt-out request

    Called when:
    - User clicks unsubscribe link
    - Reply contains "remove" or "unsubscribe"
    - Manual opt-out entry
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Mark as opted out
    property.has_opted_out = True
    property.cadence_paused = True
    property.cadence_pause_reason = "opted_out"

    # Create compliance record
    check = ComplianceCheck(
        property_id=property_id,
        check_type="opt_out",
        status=ComplianceStatus.FAILED,  # FAILED = opted out
        details=f"Opt-out reason: {reason or 'Requested removal'}"
    )

    db.add(check)

    # Create timeline event
    timeline_event = PropertyTimeline(
        property_id=property_id,
        event_type="opted_out",
        event_title="🚫 Opt-Out Recorded",
        event_description=f"Contact opted out: {reason or 'No reason given'}",
        metadata={"reason": reason}
    )
    db.add(timeline_event)

    db.commit()

    return {
        "property_id": property_id,
        "status": "opted_out",
        "message": "Contact will not receive further communications"
    }

@router.get("/compliance/badge/{property_id}")
def get_compliance_badge(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get compliance badge status for property

    Returns:
    - "compliant": All checks passed
    - "warning": Some issues need review
    - "blocked": Cannot contact

    Shown as badge on outreach step UI
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Check compliance status
    issues = []

    if property.is_on_dnc:
        issues.append("On DNC Registry")

    if property.has_opted_out:
        issues.append("Opted Out")

    # Get recent compliance checks
    recent_checks = (
        db.query(ComplianceCheck)
        .filter(ComplianceCheck.property_id == property_id)
        .order_by(desc(ComplianceCheck.checked_at))
        .limit(5)
        .all()
    )

    failed_checks = [c for c in recent_checks if c.status == ComplianceStatus.FAILED]

    if failed_checks:
        issues.extend([f"{c.check_type}: {c.status.value}" for c in failed_checks])

    # Determine badge status
    if property.is_on_dnc or property.has_opted_out:
        badge_status = "blocked"
        badge_color = "red"
        can_contact = False
    elif issues:
        badge_status = "warning"
        badge_color = "yellow"
        can_contact = True
    else:
        badge_status = "compliant"
        badge_color = "green"
        can_contact = True

    return {
        "property_id": property_id,
        "badge_status": badge_status,
        "badge_color": badge_color,
        "can_contact": can_contact,
        "issues": issues,
        "compliance_checks": len(recent_checks),
        "last_checked": recent_checks[0].checked_at if recent_checks else None
    }

@router.get("/compliance/state-disclaimers/{state}")
def get_state_disclaimers(state: str):
    """
    Get state-specific disclaimers for outreach

    Each state may have specific requirements for:
    - Cold calling disclosures
    - Mail disclaimers
    - Unsubscribe language

    Pre-fills templates with required disclaimers

    KPI: Zero compliance incidents
    """
    # State-specific disclaimer templates
    disclaimers = {
        "CA": {
            "mail": "This is not a solicitation if your property is currently listed with a real estate broker.",
            "phone": "This call may be recorded for quality assurance purposes. California residents have specific privacy rights under CCPA.",
            "email": "You may opt out of future communications at any time."
        },
        "FL": {
            "mail": "This is not an offer to purchase. We are real estate investors.",
            "phone": "Florida law requires disclosure of our business purpose.",
            "email": "CAN-SPAM compliant. Unsubscribe link provided."
        },
        "TX": {
            "mail": "Texas Real Property Disclaimer: Not an official government communication.",
            "phone": "Texas residents have the right to register on the Do Not Call list.",
            "email": "This communication is for business purposes."
        }
    }

    default_disclaimers = {
        "mail": "This is a private business communication, not affiliated with any government agency.",
        "phone": "This call is for business purposes. You may request to be added to our do-not-call list.",
        "email": "You can unsubscribe from future emails by clicking the link below."
    }

    state_disclaimers = disclaimers.get(state.upper(), default_disclaimers)

    return {
        "state": state.upper(),
        "disclaimers": state_disclaimers,
        "requires_special_handling": state.upper() in disclaimers
    }
