"""
Lease and Rent Roll Parsing Module.

Extracts structured data from lease documents and rent rolls using
multiple parsing strategies (Tika, Unstructured, regex patterns).
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, date
import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class LeaseData:
    """Structured lease data."""
    document_id: str
    tenant_name: str
    property_address: str
    unit_number: Optional[str] = None
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    lease_term_months: Optional[int] = None
    renewal_options: Optional[str] = None
    parking_spaces: Optional[int] = None
    utilities_included: Optional[str] = None
    pet_policy: Optional[str] = None
    late_fee: Optional[float] = None
    notice_period_days: Optional[int] = None
    landlord_name: Optional[str] = None
    landlord_contact: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    special_terms: Optional[str] = None
    confidence_score: float = 0.0


class LeaseParser:
    """Parser for lease documents."""

    def __init__(self):
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for extraction."""
        return {
            'monthly_rent': re.compile(
                r'(?:monthly\s+rent|rent\s+amount|monthly\s+payment)'
                r'[\s:$]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                re.IGNORECASE
            ),
            'security_deposit': re.compile(
                r'(?:security\s+deposit|deposit)'
                r'[\s:$]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                re.IGNORECASE
            ),
            'lease_start': re.compile(
                r'(?:lease\s+start|commencement\s+date|start\s+date)'
                r'[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                re.IGNORECASE
            ),
            'lease_end': re.compile(
                r'(?:lease\s+end|expiration\s+date|end\s+date|termination)'
                r'[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                re.IGNORECASE
            ),
            'tenant_name': re.compile(
                r'(?:tenant|lessee|renter)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                re.IGNORECASE
            ),
            'email': re.compile(
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ),
            'phone': re.compile(
                r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
            ),
            'unit_number': re.compile(
                r'(?:unit|apt|apartment|suite)[\s#:]*([A-Z0-9]+)',
                re.IGNORECASE
            ),
            'parking_spaces': re.compile(
                r'(\d+)\s+(?:parking\s+space|parking|space)',
                re.IGNORECASE
            ),
            'late_fee': re.compile(
                r'late\s+fee[\s:$]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                re.IGNORECASE
            ),
        }

    def parse_text(
        self,
        text: str,
        document_id: str,
        property_address: str
    ) -> LeaseData:
        """
        Parse lease data from text.

        Args:
            text: Raw text from document
            document_id: Unique document identifier
            property_address: Property address

        Returns:
            Structured lease data
        """
        logger.info(f"Parsing lease document {document_id}")

        # Extract fields using regex
        monthly_rent = self._extract_currency(text, 'monthly_rent')
        security_deposit = self._extract_currency(text, 'security_deposit')
        late_fee = self._extract_currency(text, 'late_fee')

        lease_start = self._extract_date(text, 'lease_start')
        lease_end = self._extract_date(text, 'lease_end')

        # Calculate lease term
        lease_term = None
        if lease_start and lease_end:
            delta = lease_end - lease_start
            lease_term = delta.days // 30  # Approximate months

        # Extract other fields
        tenant_name = self._extract_field(text, 'tenant_name')
        unit_number = self._extract_field(text, 'unit_number')
        tenant_email = self._extract_field(text, 'email')
        tenant_phone = self._extract_field(text, 'phone')
        parking_spaces = self._extract_int(text, 'parking_spaces')

        # Check for common terms
        utilities_included = self._check_utilities(text)
        pet_policy = self._check_pet_policy(text)

        # Calculate confidence score
        confidence = self._calculate_confidence(
            monthly_rent, security_deposit, lease_start, lease_end,
            tenant_name, property_address
        )

        lease_data = LeaseData(
            document_id=document_id,
            tenant_name=tenant_name or "Unknown",
            property_address=property_address,
            unit_number=unit_number,
            lease_start_date=lease_start,
            lease_end_date=lease_end,
            monthly_rent=monthly_rent,
            security_deposit=security_deposit,
            lease_term_months=lease_term,
            parking_spaces=parking_spaces,
            utilities_included=utilities_included,
            pet_policy=pet_policy,
            late_fee=late_fee,
            tenant_email=tenant_email,
            tenant_phone=tenant_phone,
            confidence_score=confidence
        )

        logger.info(
            f"Parsed lease {document_id}: tenant={tenant_name}, "
            f"rent=${monthly_rent}, confidence={confidence:.2f}"
        )

        return lease_data

    def _extract_currency(self, text: str, pattern_name: str) -> Optional[float]:
        """Extract currency value."""
        match = self.patterns[pattern_name].search(text)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                return float(value_str)
            except ValueError:
                return None
        return None

    def _extract_date(self, text: str, pattern_name: str) -> Optional[date]:
        """Extract date value."""
        match = self.patterns[pattern_name].search(text)
        if match:
            date_str = match.group(1)
            # Try multiple date formats
            for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
        return None

    def _extract_field(self, text: str, pattern_name: str) -> Optional[str]:
        """Extract text field."""
        match = self.patterns[pattern_name].search(text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_int(self, text: str, pattern_name: str) -> Optional[int]:
        """Extract integer value."""
        match = self.patterns[pattern_name].search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _check_utilities(self, text: str) -> Optional[str]:
        """Check which utilities are included."""
        utilities = []
        if re.search(r'water\s+included', text, re.IGNORECASE):
            utilities.append('water')
        if re.search(r'(?:electric|electricity)\s+included', text, re.IGNORECASE):
            utilities.append('electric')
        if re.search(r'gas\s+included', text, re.IGNORECASE):
            utilities.append('gas')
        if re.search(r'trash\s+included', text, re.IGNORECASE):
            utilities.append('trash')

        return ', '.join(utilities) if utilities else None

    def _check_pet_policy(self, text: str) -> Optional[str]:
        """Determine pet policy."""
        if re.search(r'no\s+pets', text, re.IGNORECASE):
            return 'No pets allowed'
        elif re.search(r'pets?\s+allowed', text, re.IGNORECASE):
            return 'Pets allowed'
        elif re.search(r'pet\s+deposit', text, re.IGNORECASE):
            return 'Pets allowed with deposit'
        return None

    def _calculate_confidence(
        self,
        monthly_rent: Optional[float],
        security_deposit: Optional[float],
        lease_start: Optional[date],
        lease_end: Optional[date],
        tenant_name: Optional[str],
        property_address: str
    ) -> float:
        """Calculate extraction confidence score."""
        score = 0.0

        # Critical fields (20% each)
        if monthly_rent:
            score += 0.20
        if tenant_name:
            score += 0.20
        if property_address:
            score += 0.20

        # Important fields (10% each)
        if lease_start:
            score += 0.10
        if lease_end:
            score += 0.10
        if security_deposit:
            score += 0.10

        # Bonus for consistency
        if lease_start and lease_end and lease_end > lease_start:
            score += 0.05
        if monthly_rent and security_deposit and security_deposit >= monthly_rent:
            score += 0.05

        return min(1.0, score)


class RentRollParser:
    """Parser for rent roll spreadsheets."""

    def parse_csv(self, file_path: str, property_address: str) -> List[LeaseData]:
        """
        Parse rent roll CSV file.

        Args:
            file_path: Path to CSV file
            property_address: Property address

        Returns:
            List of lease data records
        """
        logger.info(f"Parsing rent roll: {file_path}")

        df = pd.read_csv(file_path)

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()

        leases = []

        for idx, row in df.iterrows():
            document_id = f"rent_roll_{idx}"

            # Extract fields from columns
            monthly_rent = self._get_column_value(row, ['rent', 'monthly_rent', 'rent_amount'])
            security_deposit = self._get_column_value(row, ['deposit', 'security_deposit'])
            tenant_name = self._get_column_value(row, ['tenant', 'tenant_name', 'name'])
            unit_number = self._get_column_value(row, ['unit', 'unit_number', 'apt'])

            # Parse dates
            lease_start = self._parse_date_column(row, ['start_date', 'lease_start'])
            lease_end = self._parse_date_column(row, ['end_date', 'lease_end'])

            lease = LeaseData(
                document_id=document_id,
                tenant_name=tenant_name or "Unknown",
                property_address=property_address,
                unit_number=str(unit_number) if unit_number is not None else None,
                lease_start_date=lease_start,
                lease_end_date=lease_end,
                monthly_rent=monthly_rent,
                security_deposit=security_deposit,
                confidence_score=0.95  # High confidence for structured data
            )

            leases.append(lease)

        logger.info(f"Parsed {len(leases)} leases from rent roll")

        return leases

    def _get_column_value(self, row: pd.Series, possible_names: List[str]) -> Optional[Any]:
        """Get value from row using multiple possible column names."""
        for name in possible_names:
            if name in row.index:
                value = row[name]
                if pd.notna(value):
                    return value
        return None

    def _parse_date_column(self, row: pd.Series, possible_names: List[str]) -> Optional[date]:
        """Parse date from column."""
        value = self._get_column_value(row, possible_names)
        if value:
            try:
                return pd.to_datetime(value).date()
            except Exception:
                return None
        return None


# Global instances
lease_parser = LeaseParser()
rent_roll_parser = RentRollParser()
