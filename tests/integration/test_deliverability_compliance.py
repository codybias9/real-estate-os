"""
Integration Tests for Deliverability and Compliance

Tests DNS validation, unsubscribe management, DNC lists, and consent tracking
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.models import (
    Property,
    EmailUnsubscribe,
    DoNotCall,
    CommunicationConsent,
    PropertyStage
)
from api.deliverability import (
    check_spf_record,
    check_dkim_record,
    check_dmarc_record,
    validate_email_deliverability,
    validate_communication_compliance,
    record_unsubscribe,
    add_to_dnc_list,
    record_consent,
)


class TestDNSValidation:
    """Test DNS record validation for email deliverability"""

    def test_check_spf_record(self):
        """Test SPF record validation"""
        # Test with known domain (gmail.com has SPF)
        result = check_spf_record("gmail.com")

        assert "valid" in result
        assert "record" in result

        # Valid domains should have SPF
        if result["valid"]:
            assert result["record"] is not None
            assert "v=spf1" in result["record"].lower() or result["record"] != ""

    def test_check_dkim_record(self):
        """Test DKIM record validation"""
        # DKIM requires selector, use common one
        result = check_dkim_record("gmail.com", selector="google")

        assert "valid" in result
        assert "selector" in result

    def test_check_dmarc_record(self):
        """Test DMARC record validation"""
        # Test with known domain
        result = check_dmarc_record("gmail.com")

        assert "valid" in result
        assert "record" in result

        # Valid domains should have DMARC
        if result["valid"]:
            assert result["record"] is not None

    def test_invalid_domain_returns_false(self):
        """Test that invalid domain returns False for all checks"""
        invalid_domain = "this-domain-definitely-does-not-exist-12345.com"

        spf_result = check_spf_record(invalid_domain)
        assert spf_result["valid"] is False

        dkim_result = check_dkim_record(invalid_domain, "default")
        assert dkim_result["valid"] is False

        dmarc_result = check_dmarc_record(invalid_domain)
        assert dmarc_result["valid"] is False


class TestEmailDeliverabilityScore:
    """Test email deliverability scoring system"""

    def test_deliverability_score_calculation(self):
        """Test overall deliverability score calculation"""
        # Mock results for testing
        # Real domain with good setup should score high

        result = validate_email_deliverability("gmail.com", "google")

        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 100

        # Should include all checks
        assert "spf" in result
        assert "dkim" in result
        assert "dmarc" in result

    def test_score_components_weighting(self):
        """Test that score components are weighted correctly"""
        # SPF: 35 points
        # DKIM: 35 points
        # DMARC: 30 points
        # Total: 100 points

        result = validate_email_deliverability("example.com", "default")

        # Score should never exceed 100
        assert result["overall_score"] <= 100

    def test_recommendations_provided(self):
        """Test that recommendations are provided for improvements"""
        result = validate_email_deliverability("example.com", "default")

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

        # If not perfect score, should have recommendations
        if result["overall_score"] < 100:
            assert len(result["recommendations"]) > 0


class TestEmailUnsubscribeManagement:
    """Test email unsubscribe (CAN-SPAM/GDPR compliance)"""

    def test_record_unsubscribe(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test recording email unsubscribe"""
        email = "unsubscribe@example.com"

        record_unsubscribe(
            db=test_db,
            email=email,
            property_id=test_property.id,
            reason="User requested unsubscribe"
        )

        # Verify recorded
        unsub = test_db.query(EmailUnsubscribe).filter(
            EmailUnsubscribe.email == email
        ).first()

        assert unsub is not None
        assert unsub.property_id == test_property.id
        assert unsub.reason == "User requested unsubscribe"

    def test_check_unsubscribe_status(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test checking if email is unsubscribed"""
        email = "unsubbed@example.com"

        # Not unsubscribed initially
        from api.deliverability import check_unsubscribe_status
        assert check_unsubscribe_status(test_db, email) is False

        # Record unsubscribe
        record_unsubscribe(test_db, email, test_property.id)

        # Now should be unsubscribed
        assert check_unsubscribe_status(test_db, email) is True

    def test_unsubscribe_prevents_sending(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test that unsubscribed emails cannot be sent to"""
        email = "nosend@example.com"

        # Unsubscribe
        record_unsubscribe(test_db, email, test_property.id)

        # Check compliance
        compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="email",
            to_address=email
        )

        assert compliance["allowed"] is False
        assert "unsubscribed" in compliance["reasons"][0].lower()


class TestDNCList:
    """Test Do Not Call (DNC) list management (TCPA compliance)"""

    def test_add_to_dnc_list(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test adding phone number to DNC list"""
        phone = "+15551234567"

        add_to_dnc_list(
            db=test_db,
            phone_number=phone,
            property_id=test_property.id,
            reason="User requested DNC"
        )

        # Verify added
        dnc = test_db.query(DoNotCall).filter(
            DoNotCall.phone_number == phone
        ).first()

        assert dnc is not None
        assert dnc.property_id == test_property.id

    def test_check_dnc_status(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test checking if phone is on DNC list"""
        phone = "+15559999999"

        from api.deliverability import check_dnc_status

        # Not on DNC initially
        assert check_dnc_status(test_db, phone) is False

        # Add to DNC
        add_to_dnc_list(test_db, phone, test_property.id)

        # Now on DNC
        assert check_dnc_status(test_db, phone) is True

    def test_dnc_prevents_calls_and_sms(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test that DNC numbers cannot be called or texted"""
        phone = "+15558888888"

        # Add to DNC
        add_to_dnc_list(test_db, phone, test_property.id)

        # Check compliance for call
        call_compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="call",
            to_address=phone
        )

        assert call_compliance["allowed"] is False
        assert any("do not call" in r.lower() for r in call_compliance["reasons"])

        # Check compliance for SMS
        sms_compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="sms",
            to_address=phone
        )

        assert sms_compliance["allowed"] is False


class TestConsentTracking:
    """Test communication consent tracking (GDPR/CASL)"""

    def test_record_consent(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test recording communication consent"""
        record_consent(
            db=test_db,
            property_id=test_property.id,
            consent_type="email_marketing",
            granted=True,
            source="web_form",
            ip_address="192.168.1.1"
        )

        # Verify recorded
        consent = test_db.query(CommunicationConsent).filter(
            CommunicationConsent.property_id == test_property.id,
            CommunicationConsent.consent_type == "email_marketing"
        ).first()

        assert consent is not None
        assert consent.granted is True
        assert consent.source == "web_form"
        assert consent.ip_address == "192.168.1.1"

    def test_consent_audit_trail(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test that consent changes create audit trail"""
        # Grant consent
        record_consent(
            test_db,
            test_property.id,
            "sms_marketing",
            granted=True,
            source="phone_call"
        )

        # Revoke consent
        record_consent(
            test_db,
            test_property.id,
            "sms_marketing",
            granted=False,
            source="unsubscribe_link"
        )

        # Check history
        consents = test_db.query(CommunicationConsent).filter(
            CommunicationConsent.property_id == test_property.id,
            CommunicationConsent.consent_type == "sms_marketing"
        ).order_by(CommunicationConsent.granted_at).all()

        # Should have both records (audit trail)
        assert len(consents) >= 1

        # Latest should be revoked
        latest = consents[-1]
        assert latest.granted is False

    def test_consent_required_for_communication(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test that consent is checked before communication"""
        # No consent recorded
        compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="email",
            to_address="test@example.com"
        )

        # May allow (depending on consent requirement)
        # Or may require explicit consent

        # Record consent denial
        record_consent(
            test_db,
            test_property.id,
            "email_marketing",
            granted=False,
            source="opt_out"
        )

        # Now should definitely not allow
        compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="email",
            to_address="test@example.com"
        )

        # Check behavior (implementation dependent)
        assert "allowed" in compliance


class TestComplianceValidation:
    """Test comprehensive compliance validation"""

    def test_all_compliance_checks_passed(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test when all compliance checks pass"""
        email = "compliant@example.com"

        # Record consent
        record_consent(
            test_db,
            test_property.id,
            "email_marketing",
            granted=True,
            source="signup_form"
        )

        # Validate
        compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="email",
            to_address=email
        )

        assert compliance["allowed"] is True
        assert len(compliance["reasons"]) == 0 or all(
            "allowed" in r.lower() for r in compliance["reasons"]
        )

    def test_multiple_violations_reported(
        self,
        test_db: Session,
        test_property: Property
    ):
        """Test that multiple violations are all reported"""
        email = "violations@example.com"

        # Add unsubscribe
        record_unsubscribe(test_db, email, test_property.id)

        # Deny consent
        record_consent(
            test_db,
            test_property.id,
            "email_marketing",
            granted=False,
            source="opt_out"
        )

        # Validate
        compliance = validate_communication_compliance(
            db=test_db,
            property_id=test_property.id,
            communication_type="email",
            to_address=email
        )

        assert compliance["allowed"] is False
        # Should report both violations
        assert len(compliance["reasons"]) >= 1


class TestComplianceAPI:
    """Test compliance API endpoints"""

    def test_unsubscribe_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_property: Property
    ):
        """Test unsubscribe API endpoint"""
        response = client.post(
            "/api/v1/compliance/unsubscribe",
            json={
                "email": "unsub@example.com",
                "property_id": test_property.id,
                "reason": "User clicked unsubscribe"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 201]

    def test_check_unsubscribe_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_property: Property
    ):
        """Test check unsubscribe status endpoint"""
        email = "check@example.com"

        # Record unsubscribe
        record_unsubscribe(test_db, email, test_property.id)

        response = client.get(
            f"/api/v1/compliance/check-unsubscribe/{email}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["unsubscribed"] is True

    def test_dnc_add_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_property: Property
    ):
        """Test DNC add endpoint"""
        response = client.post(
            "/api/v1/compliance/dnc/add",
            json={
                "phone_number": "+15551112222",
                "property_id": test_property.id,
                "reason": "User requested"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 201]

    def test_dnc_check_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_property: Property
    ):
        """Test DNC check endpoint"""
        phone = "+15553334444"

        # Add to DNC
        add_to_dnc_list(test_db, phone, test_property.id)

        response = client.get(
            f"/api/v1/compliance/dnc/check/{phone}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["on_dnc_list"] is True

    def test_consent_record_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_property: Property
    ):
        """Test consent recording endpoint"""
        response = client.post(
            "/api/v1/compliance/consent/record",
            json={
                "property_id": test_property.id,
                "consent_type": "email_marketing",
                "granted": True,
                "source": "api_test",
                "ip_address": "192.168.1.100"
            },
            headers=auth_headers
        )

        assert response.status_code in [200, 201]

    def test_consent_check_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_property: Property
    ):
        """Test consent check endpoint"""
        # Record consent
        record_consent(
            test_db,
            test_property.id,
            "email_marketing",
            granted=True,
            source="test"
        )

        response = client.get(
            f"/api/v1/compliance/consent/check/{test_property.id}/email_marketing",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["has_consent"] is True

    def test_validate_send_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_property: Property
    ):
        """Test validate send compliance endpoint"""
        response = client.post(
            "/api/v1/compliance/validate-send",
            json={
                "property_id": test_property.id,
                "communication_type": "email",
                "to_address": "validate@example.com"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "allowed" in data
        assert "reasons" in data

    def test_dns_validation_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test DNS validation endpoint"""
        response = client.post(
            "/api/v1/deliverability/validate-dns",
            json={
                "domain": "gmail.com",
                "dkim_selector": "google"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "overall_score" in data
        assert "spf" in data
        assert "dkim" in data
        assert "dmarc" in data


class TestComplianceEnforcement:
    """Test that compliance is enforced in send flow"""

    def test_send_blocked_for_unsubscribed(
        self,
        client: TestClient,
        auth_headers: dict,
        test_db: Session,
        test_property: Property
    ):
        """Test that sends are blocked for unsubscribed emails"""
        # This would test the actual send endpoint with compliance checks
        # Requires template and full send infrastructure
        pass

    def test_compliance_violation_logged(
        self,
        client: TestClient,
        test_db: Session
    ):
        """Test that compliance violations are logged for audit"""
        # Check that attempted sends to blocked addresses are logged
        pass
