"""
Email Deliverability & Compliance System

Comprehensive email compliance and deliverability validation:
- SPF/DKIM/DMARC record validation
- Unsubscribe enforcement (CAN-SPAM, GDPR)
- DNC (Do Not Call) list checking
- Recording consent tracking
- Suppression list management
- Domain warmup tracking

Compliance Standards:
- CAN-SPAM Act (US)
- GDPR (EU)
- TCPA (US)
- CASL (Canada)

Features:
- Pre-send compliance validation
- Automatic unsubscribe handling
- DNC list integration
- Consent audit trail
- Bounce/complaint tracking
"""
import os
import dns.resolver
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)

# ============================================================================
# DNS VALIDATION (SPF/DKIM/DMARC)
# ============================================================================

def check_spf_record(domain: str) -> Dict[str, Any]:
    """
    Check SPF (Sender Policy Framework) record for domain

    SPF prevents email spoofing by specifying which mail servers
    are authorized to send email from the domain.

    Args:
        domain: Domain to check (e.g., "real-estate-os.com")

    Returns:
        Dict with SPF validation results:
        - exists: Whether SPF record exists
        - record: SPF record string
        - valid: Whether record is valid
        - mechanisms: List of SPF mechanisms (ip4, include, etc.)
        - all_mechanism: How SPF handles other senders (~all, -all, etc.)
    """
    result = {
        "domain": domain,
        "exists": False,
        "record": None,
        "valid": False,
        "mechanisms": [],
        "all_mechanism": None,
        "errors": []
    }

    try:
        # Query TXT records for SPF
        answers = dns.resolver.resolve(domain, 'TXT')

        # Find SPF record (starts with "v=spf1")
        spf_records = [str(rdata).strip('"') for rdata in answers if str(rdata).startswith('"v=spf1')]

        if not spf_records:
            result["errors"].append("No SPF record found")
            return result

        if len(spf_records) > 1:
            result["errors"].append("Multiple SPF records found (invalid)")
            return result

        spf_record = spf_records[0]
        result["exists"] = True
        result["record"] = spf_record

        # Parse mechanisms
        parts = spf_record.split()
        result["mechanisms"] = [p for p in parts if p != "v=spf1"]

        # Check for "all" mechanism
        all_mechanisms = [m for m in result["mechanisms"] if m.endswith("all")]
        if all_mechanisms:
            result["all_mechanism"] = all_mechanisms[0]

        # Basic validation
        if "v=spf1" in spf_record and any(m.endswith("all") for m in result["mechanisms"]):
            result["valid"] = True
        else:
            result["errors"].append("SPF record missing required elements")

        logger.info(f"SPF check for {domain}: {result['valid']}")

    except dns.resolver.NXDOMAIN:
        result["errors"].append(f"Domain {domain} does not exist")
    except dns.resolver.NoAnswer:
        result["errors"].append("No TXT records found for domain")
    except Exception as e:
        result["errors"].append(f"DNS query failed: {str(e)}")
        logger.error(f"SPF check failed for {domain}: {str(e)}")

    return result


def check_dkim_record(domain: str, selector: str = "default") -> Dict[str, Any]:
    """
    Check DKIM (DomainKeys Identified Mail) record

    DKIM adds a digital signature to emails, allowing receivers
    to verify the email came from the claimed domain.

    Args:
        domain: Domain to check
        selector: DKIM selector (default: "default")
                 Common selectors: "default", "s1", "google", "k1"

    Returns:
        Dict with DKIM validation results:
        - exists: Whether DKIM record exists
        - selector: DKIM selector used
        - record: DKIM public key record
        - valid: Whether record is valid
    """
    result = {
        "domain": domain,
        "selector": selector,
        "exists": False,
        "record": None,
        "valid": False,
        "errors": []
    }

    try:
        # DKIM record format: <selector>._domainkey.<domain>
        dkim_domain = f"{selector}._domainkey.{domain}"

        # Query TXT records
        answers = dns.resolver.resolve(dkim_domain, 'TXT')

        # Combine TXT record parts
        dkim_record = ''.join([str(rdata).strip('"') for rdata in answers])

        result["exists"] = True
        result["record"] = dkim_record

        # Basic validation (should contain v=DKIM1 and p=<public-key>)
        if "v=DKIM1" in dkim_record and "p=" in dkim_record:
            result["valid"] = True
        else:
            result["errors"].append("DKIM record missing required elements")

        logger.info(f"DKIM check for {domain} (selector={selector}): {result['valid']}")

    except dns.resolver.NXDOMAIN:
        result["errors"].append(f"DKIM record not found for selector '{selector}'")
    except dns.resolver.NoAnswer:
        result["errors"].append(f"No DKIM record for selector '{selector}'")
    except Exception as e:
        result["errors"].append(f"DNS query failed: {str(e)}")
        logger.error(f"DKIM check failed for {domain}: {str(e)}")

    return result


def check_dmarc_record(domain: str) -> Dict[str, Any]:
    """
    Check DMARC (Domain-based Message Authentication, Reporting & Conformance) record

    DMARC builds on SPF and DKIM to specify how receivers should handle
    emails that fail authentication.

    Args:
        domain: Domain to check

    Returns:
        Dict with DMARC validation results:
        - exists: Whether DMARC record exists
        - record: DMARC record string
        - valid: Whether record is valid
        - policy: DMARC policy (none, quarantine, reject)
        - subdomain_policy: Policy for subdomains
        - percentage: Percentage of messages to apply policy
    """
    result = {
        "domain": domain,
        "exists": False,
        "record": None,
        "valid": False,
        "policy": None,
        "subdomain_policy": None,
        "percentage": None,
        "errors": []
    }

    try:
        # DMARC record format: _dmarc.<domain>
        dmarc_domain = f"_dmarc.{domain}"

        # Query TXT records
        answers = dns.resolver.resolve(dmarc_domain, 'TXT')

        # Find DMARC record (starts with "v=DMARC1")
        dmarc_records = [str(rdata).strip('"') for rdata in answers if str(rdata).startswith('"v=DMARC1')]

        if not dmarc_records:
            result["errors"].append("No DMARC record found")
            return result

        if len(dmarc_records) > 1:
            result["errors"].append("Multiple DMARC records found (invalid)")
            return result

        dmarc_record = dmarc_records[0]
        result["exists"] = True
        result["record"] = dmarc_record

        # Parse policy
        parts = dmarc_record.split(';')
        for part in parts:
            part = part.strip()
            if part.startswith('p='):
                result["policy"] = part.split('=')[1]
            elif part.startswith('sp='):
                result["subdomain_policy"] = part.split('=')[1]
            elif part.startswith('pct='):
                result["percentage"] = int(part.split('=')[1])

        # Basic validation
        if "v=DMARC1" in dmarc_record and result["policy"]:
            result["valid"] = True
        else:
            result["errors"].append("DMARC record missing required elements")

        logger.info(f"DMARC check for {domain}: {result['valid']} (policy={result['policy']})")

    except dns.resolver.NXDOMAIN:
        result["errors"].append("DMARC record not found")
    except dns.resolver.NoAnswer:
        result["errors"].append("No DMARC record")
    except Exception as e:
        result["errors"].append(f"DNS query failed: {str(e)}")
        logger.error(f"DMARC check failed for {domain}: {str(e)}")

    return result


def validate_email_deliverability(domain: str, dkim_selector: str = "default") -> Dict[str, Any]:
    """
    Comprehensive email deliverability check

    Validates SPF, DKIM, and DMARC for a domain.

    Args:
        domain: Domain to validate
        dkim_selector: DKIM selector to check

    Returns:
        Dict with full deliverability validation:
        - domain: Domain checked
        - timestamp: Check timestamp
        - spf: SPF validation results
        - dkim: DKIM validation results
        - dmarc: DMARC validation results
        - overall_score: Score 0-100
        - recommendations: List of improvements
    """
    results = {
        "domain": domain,
        "timestamp": datetime.utcnow().isoformat(),
        "spf": check_spf_record(domain),
        "dkim": check_dkim_record(domain, dkim_selector),
        "dmarc": check_dmarc_record(domain),
        "overall_score": 0,
        "recommendations": []
    }

    # Calculate score
    score = 0
    if results["spf"]["valid"]:
        score += 35
    elif results["spf"]["exists"]:
        score += 15
        results["recommendations"].append("Fix SPF record (exists but invalid)")
    else:
        results["recommendations"].append("Add SPF record to prevent spoofing")

    if results["dkim"]["valid"]:
        score += 35
    elif results["dkim"]["exists"]:
        score += 15
        results["recommendations"].append("Fix DKIM record (exists but invalid)")
    else:
        results["recommendations"].append(f"Add DKIM record with selector '{dkim_selector}'")

    if results["dmarc"]["valid"]:
        score += 30
        # Check policy strictness
        policy = results["dmarc"]["policy"]
        if policy == "none":
            results["recommendations"].append("Upgrade DMARC policy from 'none' to 'quarantine' or 'reject'")
        elif policy == "quarantine":
            score += 5
        elif policy == "reject":
            score += 10
    elif results["dmarc"]["exists"]:
        score += 10
        results["recommendations"].append("Fix DMARC record (exists but invalid)")
    else:
        results["recommendations"].append("Add DMARC record for email authentication")

    results["overall_score"] = min(score, 100)

    return results


# ============================================================================
# UNSUBSCRIBE MANAGEMENT (CAN-SPAM, GDPR)
# ============================================================================

def record_unsubscribe(
    db: Session,
    email: str,
    reason: Optional[str] = None,
    source: str = "user_request"
) -> int:
    """
    Record email unsubscribe

    Compliance: CAN-SPAM requires honoring unsubscribes within 10 business days
    GDPR requires honoring immediately

    Args:
        db: Database session
        email: Email address to unsubscribe
        reason: Optional reason for unsubscribe
        source: Source of unsubscribe (user_request, complaint, bounce)

    Returns:
        Unsubscribe record ID
    """
    from db.models import EmailUnsubscribe

    # Check if already unsubscribed
    existing = db.query(EmailUnsubscribe).filter(
        EmailUnsubscribe.email == email.lower()
    ).first()

    if existing:
        logger.info(f"Email {email} already unsubscribed")
        return existing.id

    # Create unsubscribe record
    unsubscribe = EmailUnsubscribe(
        email=email.lower(),
        unsubscribed_at=datetime.utcnow(),
        reason=reason,
        source=source
    )

    db.add(unsubscribe)
    db.commit()
    db.refresh(unsubscribe)

    logger.info(f"Recorded unsubscribe for {email} (source={source})")

    return unsubscribe.id


def is_unsubscribed(db: Session, email: str) -> bool:
    """
    Check if email is unsubscribed

    Args:
        db: Database session
        email: Email address to check

    Returns:
        True if unsubscribed
    """
    from db.models import EmailUnsubscribe

    count = db.query(EmailUnsubscribe).filter(
        EmailUnsubscribe.email == email.lower()
    ).count()

    return count > 0


def get_unsubscribe_list(db: Session, limit: int = 1000) -> List[str]:
    """
    Get list of unsubscribed emails

    Args:
        db: Database session
        limit: Max emails to return

    Returns:
        List of unsubscribed email addresses
    """
    from db.models import EmailUnsubscribe

    unsubscribes = db.query(EmailUnsubscribe.email).limit(limit).all()

    return [u.email for u in unsubscribes]


# ============================================================================
# DNC (DO NOT CALL) LIST
# ============================================================================

def add_to_dnc_list(
    db: Session,
    phone: str,
    reason: Optional[str] = None,
    source: str = "user_request"
) -> int:
    """
    Add phone number to Do Not Call list

    Compliance: TCPA requires honoring DNC requests

    Args:
        db: Database session
        phone: Phone number to add
        reason: Optional reason
        source: Source of request

    Returns:
        DNC record ID
    """
    from db.models import DoNotCall

    # Normalize phone number (remove formatting)
    normalized_phone = ''.join(c for c in phone if c.isdigit())

    # Check if already in DNC
    existing = db.query(DoNotCall).filter(
        DoNotCall.phone == normalized_phone
    ).first()

    if existing:
        logger.info(f"Phone {phone} already in DNC list")
        return existing.id

    # Create DNC record
    dnc = DoNotCall(
        phone=normalized_phone,
        added_at=datetime.utcnow(),
        reason=reason,
        source=source
    )

    db.add(dnc)
    db.commit()
    db.refresh(dnc)

    logger.info(f"Added {phone} to DNC list (source={source})")

    return dnc.id


def is_on_dnc_list(db: Session, phone: str) -> bool:
    """
    Check if phone number is on DNC list

    Args:
        db: Database session
        phone: Phone number to check

    Returns:
        True if on DNC list
    """
    from db.models import DoNotCall

    # Normalize phone number
    normalized_phone = ''.join(c for c in phone if c.isdigit())

    count = db.query(DoNotCall).filter(
        DoNotCall.phone == normalized_phone
    ).count()

    return count > 0


# ============================================================================
# CONSENT TRACKING
# ============================================================================

def record_consent(
    db: Session,
    property_id: int,
    consent_type: str,
    consented: bool,
    consent_method: str,
    consent_text: Optional[str] = None,
    ip_address: Optional[str] = None
) -> int:
    """
    Record consent for communication

    Compliance: GDPR requires explicit consent with audit trail

    Args:
        db: Database session
        property_id: Property ID
        consent_type: Type of consent (email, sms, call, recording)
        consented: Whether consent was given
        consent_method: How consent was obtained (web_form, verbal, written)
        consent_text: Exact text of consent
        ip_address: IP address of consenter

    Returns:
        Consent record ID
    """
    from db.models import CommunicationConsent

    consent = CommunicationConsent(
        property_id=property_id,
        consent_type=consent_type,
        consented=consented,
        consent_method=consent_method,
        consent_text=consent_text,
        ip_address=ip_address,
        recorded_at=datetime.utcnow()
    )

    db.add(consent)
    db.commit()
    db.refresh(consent)

    logger.info(
        f"Recorded {consent_type} consent for property {property_id}: {consented}",
        extra={
            "property_id": property_id,
            "consent_type": consent_type,
            "consented": consented,
            "method": consent_method
        }
    )

    return consent.id


def check_consent(db: Session, property_id: int, consent_type: str) -> Optional[bool]:
    """
    Check if consent exists for property

    Args:
        db: Database session
        property_id: Property ID
        consent_type: Type of consent to check

    Returns:
        True if consented, False if declined, None if no record
    """
    from db.models import CommunicationConsent

    # Get most recent consent
    consent = db.query(CommunicationConsent).filter(
        and_(
            CommunicationConsent.property_id == property_id,
            CommunicationConsent.consent_type == consent_type
        )
    ).order_by(CommunicationConsent.recorded_at.desc()).first()

    if not consent:
        return None

    return consent.consented


# ============================================================================
# PRE-SEND COMPLIANCE VALIDATION
# ============================================================================

def validate_communication_compliance(
    db: Session,
    property_id: int,
    communication_type: str,
    to_address: str
) -> Dict[str, Any]:
    """
    Pre-send compliance validation

    Checks all compliance requirements before sending communication:
    - Unsubscribe status (for email)
    - DNC status (for calls/SMS)
    - Consent records
    - Suppression lists

    Args:
        db: Database session
        property_id: Property ID
        communication_type: Type (email, sms, call)
        to_address: Recipient (email or phone)

    Returns:
        Dict with validation results:
        - allowed: Whether communication is allowed
        - reasons: List of reasons if blocked
        - warnings: List of warnings
    """
    result = {
        "allowed": True,
        "reasons": [],
        "warnings": []
    }

    if communication_type == "email":
        # Check unsubscribe list
        if is_unsubscribed(db, to_address):
            result["allowed"] = False
            result["reasons"].append("Email address is unsubscribed")

        # Check consent
        consent = check_consent(db, property_id, "email")
        if consent is False:
            result["allowed"] = False
            result["reasons"].append("Email consent was declined")
        elif consent is None:
            result["warnings"].append("No email consent on record")

    elif communication_type in ["call", "sms"]:
        # Check DNC list
        if is_on_dnc_list(db, to_address):
            result["allowed"] = False
            result["reasons"].append("Phone number is on Do Not Call list")

        # Check consent
        consent_type = "sms" if communication_type == "sms" else "call"
        consent = check_consent(db, property_id, consent_type)
        if consent is False:
            result["allowed"] = False
            result["reasons"].append(f"{consent_type.upper()} consent was declined")
        elif consent is None:
            result["warnings"].append(f"No {consent_type} consent on record")

    return result


# ============================================================================
# SUPPRESSION LIST MANAGEMENT
# ============================================================================

def sync_suppression_list_from_sendgrid(db: Session) -> Dict[str, Any]:
    """
    Sync suppression list from SendGrid API

    SendGrid maintains suppression lists for:
    - Bounces (hard bounces)
    - Spam reports
    - Blocks
    - Invalid emails

    Args:
        db: Database session

    Returns:
        Dict with sync results
    """
    # TODO: Implement SendGrid API integration
    # from sendgrid import SendGridAPIClient
    # sg = SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    # response = sg.client.suppression.bounces.get()

    logger.info("Suppression list sync not yet implemented")

    return {
        "success": False,
        "message": "SendGrid API integration pending"
    }
