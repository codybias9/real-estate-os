"""
Integration tests for lease parsing.

Tests the lease_parser module with realistic document text samples.
"""
import pytest
from datetime import date
import tempfile
import csv
from document_processing.lease_parser import (
    lease_parser,
    rent_roll_parser,
    LeaseData
)


class TestLeaseParser:
    """Test lease document parsing."""

    def test_complete_lease_document(self):
        """Test parsing a complete lease with all fields."""
        text = """
        RESIDENTIAL LEASE AGREEMENT

        Property Address: 123 Main Street, San Francisco, CA 94102
        Unit Number: Apt 4B

        TENANT: John Smith
        Email: john.smith@email.com
        Phone: (415) 555-1234

        LANDLORD: ABC Property Management

        Lease Terms:
        - Lease Start Date: 01/15/2024
        - Lease End Date: 01/14/2025
        - Monthly Rent: $3,500.00
        - Security Deposit: $7,000.00
        - Late Fee: $75.00

        Parking: 1 parking space included

        Utilities: Water included, Electric included

        Pet Policy: Pets allowed with deposit
        """

        result = lease_parser.parse_text(
            text=text,
            document_id="test_lease_001",
            property_address="123 Main Street, San Francisco, CA 94102"
        )

        # Verify all extracted fields
        assert result.document_id == "test_lease_001"
        assert result.tenant_name == "John Smith"
        assert result.property_address == "123 Main Street, San Francisco, CA 94102"
        assert result.unit_number == "4B"
        assert result.lease_start_date == date(2024, 1, 15)
        assert result.lease_end_date == date(2025, 1, 14)
        assert result.monthly_rent == 3500.0
        assert result.security_deposit == 7000.0
        assert result.late_fee == 75.0
        assert result.parking_spaces == 1
        assert "water" in result.utilities_included.lower()
        assert "electric" in result.utilities_included.lower()
        assert "deposit" in result.pet_policy.lower()
        assert result.tenant_email == "john.smith@email.com"
        assert "415" in result.tenant_phone
        assert result.confidence_score > 0.8  # High confidence
        assert result.lease_term_months == 12

    def test_minimal_lease_document(self):
        """Test parsing a lease with minimal information."""
        text = """
        Rental Agreement

        Tenant: Jane Doe
        Address: 456 Oak Ave
        Monthly Rent Amount: $2,000
        """

        result = lease_parser.parse_text(
            text=text,
            document_id="test_lease_002",
            property_address="456 Oak Ave"
        )

        assert result.tenant_name == "Jane Doe"
        assert result.monthly_rent == 2000.0
        assert result.property_address == "456 Oak Ave"
        assert result.confidence_score < 0.8  # Lower confidence due to missing fields

    def test_date_format_variations(self):
        """Test parsing different date formats."""
        test_cases = [
            ("Lease Start: 03/15/2024", date(2024, 3, 15)),
            ("Start Date: 03-15-2024", date(2024, 3, 15)),
            ("Commencement Date: 3/15/24", date(2024, 3, 15)),
        ]

        for text, expected_date in test_cases:
            result = lease_parser.parse_text(
                text=f"Tenant: Test Tenant\n{text}",
                document_id="test",
                property_address="Test Address"
            )
            assert result.lease_start_date == expected_date

    def test_currency_format_variations(self):
        """Test parsing different currency formats."""
        test_cases = [
            ("Monthly Rent: $1,500.00", 1500.0),
            ("Rent Amount: $1500", 1500.0),
            ("Monthly Payment: 1,500.00", 1500.0),
            ("Rent: 1500", 1500.0),
        ]

        for text, expected_amount in test_cases:
            result = lease_parser.parse_text(
                text=f"Tenant: Test Tenant\n{text}",
                document_id="test",
                property_address="Test Address"
            )
            assert result.monthly_rent == expected_amount

    def test_utilities_detection(self):
        """Test detection of included utilities."""
        text = """
        Utilities: Water included, Gas included, Trash included
        Tenant: Test Tenant
        """

        result = lease_parser.parse_text(
            text=text,
            document_id="test",
            property_address="Test Address"
        )

        assert result.utilities_included is not None
        assert "water" in result.utilities_included.lower()
        assert "gas" in result.utilities_included.lower()
        assert "trash" in result.utilities_included.lower()

    def test_pet_policy_detection(self):
        """Test pet policy detection."""
        test_cases = [
            ("No pets allowed on premises", "No pets allowed"),
            ("Pets are allowed with approval", "Pets allowed"),
            ("Pet deposit required: $500", "Pets allowed with deposit"),
        ]

        for text, expected_policy in test_cases:
            result = lease_parser.parse_text(
                text=f"Tenant: Test Tenant\n{text}",
                document_id="test",
                property_address="Test Address"
            )
            assert result.pet_policy is not None
            assert expected_policy.lower() in result.pet_policy.lower()

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        # High confidence: all critical fields present
        complete_text = """
        Tenant: John Smith
        Address: 123 Main St
        Monthly Rent: $2,000
        Lease Start Date: 01/01/2024
        Lease End Date: 12/31/2024
        Security Deposit: $4,000
        """

        result = lease_parser.parse_text(
            text=complete_text,
            document_id="test",
            property_address="123 Main St"
        )
        assert result.confidence_score >= 0.9

        # Low confidence: missing critical fields
        minimal_text = "Some text without clear lease information"

        result = lease_parser.parse_text(
            text=minimal_text,
            document_id="test",
            property_address="Unknown"
        )
        assert result.confidence_score < 0.5


class TestRentRollParser:
    """Test rent roll CSV parsing."""

    def test_standard_rent_roll_csv(self):
        """Test parsing a standard rent roll CSV."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Unit', 'Tenant', 'Monthly_Rent', 'Deposit',
                'Start_Date', 'End_Date'
            ])
            writer.writeheader()
            writer.writerow({
                'Unit': '101',
                'Tenant': 'Alice Johnson',
                'Monthly_Rent': '1500',
                'Deposit': '3000',
                'Start_Date': '2024-01-01',
                'End_Date': '2024-12-31'
            })
            writer.writerow({
                'Unit': '102',
                'Tenant': 'Bob Wilson',
                'Monthly_Rent': '1650',
                'Deposit': '3300',
                'Start_Date': '2024-02-01',
                'End_Date': '2025-01-31'
            })
            csv_path = f.name

        # Parse the CSV
        results = rent_roll_parser.parse_csv(
            file_path=csv_path,
            property_address="Test Property"
        )

        assert len(results) == 2

        # Check first lease
        lease1 = results[0]
        assert lease1.unit_number == '101'
        assert lease1.tenant_name == 'Alice Johnson'
        assert lease1.monthly_rent == 1500
        assert lease1.security_deposit == 3000
        assert lease1.lease_start_date == date(2024, 1, 1)
        assert lease1.lease_end_date == date(2024, 12, 31)
        assert lease1.confidence_score == 0.95  # High confidence for structured data

        # Check second lease
        lease2 = results[1]
        assert lease2.unit_number == '102'
        assert lease2.tenant_name == 'Bob Wilson'
        assert lease2.monthly_rent == 1650

    def test_rent_roll_with_missing_fields(self):
        """Test parsing rent roll with some missing fields."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            writer = csv.DictWriter(f, fieldnames=['Unit', 'Tenant', 'Rent'])
            writer.writeheader()
            writer.writerow({
                'Unit': '201',
                'Tenant': 'Charlie Brown',
                'Rent': '1800'
            })
            csv_path = f.name

        results = rent_roll_parser.parse_csv(
            file_path=csv_path,
            property_address="Test Property"
        )

        assert len(results) == 1
        lease = results[0]
        assert lease.unit_number == '201'
        assert lease.tenant_name == 'Charlie Brown'
        assert lease.monthly_rent == 1800
        assert lease.security_deposit is None
        assert lease.lease_start_date is None

    def test_rent_roll_column_name_variations(self):
        """Test parsing with different column naming conventions."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            # Use different column names
            writer = csv.DictWriter(f, fieldnames=[
                'Apt', 'Tenant_Name', 'Rent_Amount'
            ])
            writer.writeheader()
            writer.writerow({
                'Apt': '301',
                'Tenant_Name': 'Diana Prince',
                'Rent_Amount': '2000'
            })
            csv_path = f.name

        results = rent_roll_parser.parse_csv(
            file_path=csv_path,
            property_address="Test Property"
        )

        assert len(results) == 1
        lease = results[0]
        assert lease.unit_number == '301'
        assert lease.tenant_name == 'Diana Prince'
        assert lease.monthly_rent == 2000


class TestLeaseDataModel:
    """Test LeaseData dataclass."""

    def test_lease_data_creation(self):
        """Test creating a LeaseData instance."""
        lease = LeaseData(
            document_id="test_001",
            tenant_name="Test Tenant",
            property_address="123 Test St",
            monthly_rent=1500.0,
            confidence_score=0.85
        )

        assert lease.document_id == "test_001"
        assert lease.tenant_name == "Test Tenant"
        assert lease.monthly_rent == 1500.0
        assert lease.confidence_score == 0.85

        # Check optional fields default to None
        assert lease.unit_number is None
        assert lease.lease_start_date is None

    def test_lease_data_serialization(self):
        """Test converting LeaseData to dict."""
        from dataclasses import asdict

        lease = LeaseData(
            document_id="test_001",
            tenant_name="Test Tenant",
            property_address="123 Test St",
            monthly_rent=1500.0,
            lease_start_date=date(2024, 1, 1)
        )

        data_dict = asdict(lease)

        assert data_dict['document_id'] == "test_001"
        assert data_dict['monthly_rent'] == 1500.0
        assert data_dict['lease_start_date'] == date(2024, 1, 1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
