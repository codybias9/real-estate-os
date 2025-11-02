"""
Lease and Rent Roll Document Parser

This module extracts structured data from lease agreements and rent roll documents
using Apache Tika for format conversion and Unstructured for intelligent parsing.

Supports:
- PDF lease agreements
- Excel/CSV rent rolls
- Scanned documents (OCR via Tesseract)
- Multi-page leases with varying layouts
"""

import os
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict
import json

# Document processing libraries
try:
    from tika import parser as tika_parser
    from unstructured.partition.auto import partition
    from unstructured.cleaners.core import clean, group_broken_paragraphs
    import pandas as pd
except ImportError:
    # Fallback for testing
    tika_parser = None
    partition = None
    pd = None


logger = logging.getLogger(__name__)


@dataclass
class LeaseTerms:
    """Structured lease terms extracted from document"""
    property_address: Optional[str] = None
    unit_number: Optional[str] = None
    tenant_name: Optional[str] = None
    landlord_name: Optional[str] = None

    # Financial terms
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    pet_deposit: Optional[float] = None

    # Dates
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    move_in_date: Optional[date] = None

    # Unit details
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None

    # Lease type
    lease_type: Optional[str] = None  # "fixed", "month-to-month", etc.

    # Additional terms
    utilities_included: List[str] = None
    parking_spaces: Optional[int] = None
    pets_allowed: Optional[bool] = None

    # Metadata
    confidence_score: float = 0.0
    extraction_errors: List[str] = None

    def __post_init__(self):
        if self.utilities_included is None:
            self.utilities_included = []
        if self.extraction_errors is None:
            self.extraction_errors = []


@dataclass
class RentRollEntry:
    """Single entry from rent roll"""
    unit_number: str
    tenant_name: str
    monthly_rent: float
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    security_deposit: Optional[float] = None
    status: str = "occupied"  # occupied, vacant, notice
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None


@dataclass
class RentRoll:
    """Complete rent roll for property"""
    property_name: str
    property_address: str
    as_of_date: date
    entries: List[RentRollEntry]

    # Summary statistics
    total_units: int = 0
    occupied_units: int = 0
    vacant_units: int = 0
    total_monthly_rent: float = 0.0
    occupancy_rate: float = 0.0

    def calculate_summary(self):
        """Calculate summary statistics from entries"""
        self.total_units = len(self.entries)
        self.occupied_units = sum(1 for e in self.entries if e.status == "occupied")
        self.vacant_units = sum(1 for e in self.entries if e.status == "vacant")
        self.total_monthly_rent = sum(e.monthly_rent for e in self.entries if e.status == "occupied")
        self.occupancy_rate = self.occupied_units / self.total_units if self.total_units > 0 else 0.0


class LeaseParser:
    """Parser for lease agreement documents"""

    def __init__(self):
        """Initialize lease parser"""
        self.tika_server_url = os.getenv("TIKA_SERVER_URL", "http://localhost:9998")

    def parse_lease_document(self, file_path: str) -> LeaseTerms:
        """
        Parse lease document and extract structured terms

        Args:
            file_path: Path to lease document (PDF, DOC, etc.)

        Returns:
            LeaseTerms object with extracted data
        """
        logger.info(f"Parsing lease document: {file_path}")

        # Extract text using Tika
        text = self._extract_text_with_tika(file_path)

        # Parse with Unstructured for better structure
        elements = self._partition_document(file_path)

        # Extract lease terms
        terms = LeaseTerms()

        # Extract property address
        terms.property_address = self._extract_address(text)

        # Extract unit number
        terms.unit_number = self._extract_unit_number(text)

        # Extract tenant name
        terms.tenant_name = self._extract_tenant_name(text)

        # Extract landlord name
        terms.landlord_name = self._extract_landlord_name(text)

        # Extract financial terms
        terms.monthly_rent = self._extract_monthly_rent(text)
        terms.security_deposit = self._extract_security_deposit(text)
        terms.pet_deposit = self._extract_pet_deposit(text)

        # Extract dates
        terms.lease_start_date = self._extract_lease_start_date(text)
        terms.lease_end_date = self._extract_lease_end_date(text)

        # Extract unit details
        terms.bedrooms = self._extract_bedrooms(text)
        terms.bathrooms = self._extract_bathrooms(text)
        terms.square_feet = self._extract_square_feet(text)

        # Extract lease type
        terms.lease_type = self._extract_lease_type(text)

        # Extract utilities
        terms.utilities_included = self._extract_utilities(text)

        # Extract parking
        terms.parking_spaces = self._extract_parking(text)

        # Extract pet policy
        terms.pets_allowed = self._extract_pets_allowed(text)

        # Calculate confidence score
        terms.confidence_score = self._calculate_confidence(terms)

        logger.info(f"Extracted lease terms with {terms.confidence_score:.2%} confidence")

        return terms

    def _extract_text_with_tika(self, file_path: str) -> str:
        """Extract raw text from document using Apache Tika"""
        if tika_parser:
            parsed = tika_parser.from_file(file_path, serverEndpoint=self.tika_server_url)
            return parsed.get("content", "")
        else:
            # Fallback: read as text if possible
            with open(file_path, 'r', errors='ignore') as f:
                return f.read()

    def _partition_document(self, file_path: str) -> List:
        """Partition document into structured elements"""
        if partition:
            elements = partition(filename=file_path)
            return elements
        else:
            return []

    def _extract_address(self, text: str) -> Optional[str]:
        """Extract property address from text"""
        # Common patterns for addresses in leases
        patterns = [
            r'(?i)property\s+(?:address|located at):\s*([^\n]+)',
            r'(?i)premises:\s*([^\n]+)',
            r'(?i)leased\s+premises?:\s*([^\n]+)',
            r'(\d+\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Circle|Cir|Place|Pl)[,\s]+[A-Z][a-z]+[,\s]+[A-Z]{2}\s+\d{5})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_unit_number(self, text: str) -> Optional[str]:
        """Extract unit number"""
        patterns = [
            r'(?i)unit\s+(?:number|#|no\.?)?\s*([A-Z0-9-]+)',
            r'(?i)apartment\s+(?:number|#|no\.?)?\s*([A-Z0-9-]+)',
            r'(?i)suite\s+(?:number|#|no\.?)?\s*([A-Z0-9-]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_tenant_name(self, text: str) -> Optional[str]:
        """Extract tenant name"""
        patterns = [
            r'(?i)tenant:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?i)lessee:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?i)resident:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_landlord_name(self, text: str) -> Optional[str]:
        """Extract landlord name"""
        patterns = [
            r'(?i)landlord:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?i)lessor:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?i)owner:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _extract_monthly_rent(self, text: str) -> Optional[float]:
        """Extract monthly rent amount"""
        patterns = [
            r'(?i)monthly\s+rent:\s*\$?\s*([\d,]+(?:\.\d{2})?)',
            r'(?i)rent\s+amount:\s*\$?\s*([\d,]+(?:\.\d{2})?)',
            r'(?i)base\s+rent:\s*\$?\s*([\d,]+(?:\.\d{2})?)',
            r'\$\s*([\d,]+(?:\.\d{2})?)\s+per\s+month'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue

        return None

    def _extract_security_deposit(self, text: str) -> Optional[float]:
        """Extract security deposit amount"""
        patterns = [
            r'(?i)security\s+deposit:\s*\$?\s*([\d,]+(?:\.\d{2})?)',
            r'(?i)deposit:\s*\$?\s*([\d,]+(?:\.\d{2})?)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue

        return None

    def _extract_pet_deposit(self, text: str) -> Optional[float]:
        """Extract pet deposit amount"""
        pattern = r'(?i)pet\s+(?:deposit|fee):\s*\$?\s*([\d,]+(?:\.\d{2})?)'
        match = re.search(pattern, text)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                return None
        return None

    def _extract_lease_start_date(self, text: str) -> Optional[date]:
        """Extract lease start date"""
        patterns = [
            r'(?i)lease\s+(?:start|commencement)\s+date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)term\s+begins?:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)from\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+to'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                return self._parse_date(date_str)

        return None

    def _extract_lease_end_date(self, text: str) -> Optional[date]:
        """Extract lease end date"""
        patterns = [
            r'(?i)lease\s+(?:end|expiration|termination)\s+date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)term\s+ends?:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)to\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                return self._parse_date(date_str)

        return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string into date object"""
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%m/%d/%y",
            "%m-%d-%y",
            "%d/%m/%Y",
            "%d-%m-%Y"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_bedrooms(self, text: str) -> Optional[int]:
        """Extract number of bedrooms"""
        pattern = r'(\d+)\s+bed(?:room)?s?'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_bathrooms(self, text: str) -> Optional[float]:
        """Extract number of bathrooms"""
        pattern = r'([\d\.]+)\s+bath(?:room)?s?'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_square_feet(self, text: str) -> Optional[int]:
        """Extract square footage"""
        patterns = [
            r'([\d,]+)\s+(?:sq\.?\s*ft|square\s+feet)',
            r'([\d,]+)\s+sf\b'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sqft_str = match.group(1).replace(',', '')
                return int(sqft_str)

        return None

    def _extract_lease_type(self, text: str) -> Optional[str]:
        """Extract lease type"""
        if re.search(r'(?i)month[-\s]to[-\s]month', text):
            return "month-to-month"
        elif re.search(r'(?i)fixed[-\s]term|term\s+lease', text):
            return "fixed"
        return None

    def _extract_utilities(self, text: str) -> List[str]:
        """Extract utilities included in rent"""
        utilities = []
        utility_patterns = {
            "water": r'\b(?i)water\b',
            "sewer": r'\b(?i)sewer\b',
            "trash": r'\b(?i)trash|garbage\b',
            "electric": r'\b(?i)electric(?:ity)?\b',
            "gas": r'\b(?i)gas\b',
            "internet": r'\b(?i)internet|wifi\b',
            "cable": r'\b(?i)cable\b'
        }

        for utility, pattern in utility_patterns.items():
            if re.search(pattern, text):
                # Check if it says "included"
                context_pattern = f"{pattern}.*?(?i)included"
                if re.search(context_pattern, text):
                    utilities.append(utility)

        return utilities

    def _extract_parking(self, text: str) -> Optional[int]:
        """Extract number of parking spaces"""
        pattern = r'(\d+)\s+parking\s+(?:space|spot)s?'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _extract_pets_allowed(self, text: str) -> Optional[bool]:
        """Extract pet policy"""
        if re.search(r'(?i)pets?\s+(?:are\s+)?allowed', text):
            return True
        elif re.search(r'(?i)no\s+pets?', text):
            return False
        return None

    def _calculate_confidence(self, terms: LeaseTerms) -> float:
        """Calculate confidence score based on extracted fields"""
        total_fields = 0
        extracted_fields = 0

        # Critical fields (weighted more)
        critical_fields = [
            ('property_address', 2),
            ('tenant_name', 2),
            ('monthly_rent', 3),
            ('lease_start_date', 2),
            ('lease_end_date', 2)
        ]

        for field, weight in critical_fields:
            total_fields += weight
            if getattr(terms, field) is not None:
                extracted_fields += weight

        # Optional fields (weighted less)
        optional_fields = [
            'unit_number', 'landlord_name', 'security_deposit',
            'bedrooms', 'bathrooms', 'square_feet', 'lease_type'
        ]

        for field in optional_fields:
            total_fields += 1
            if getattr(terms, field) is not None:
                extracted_fields += 1

        return extracted_fields / total_fields if total_fields > 0 else 0.0


class RentRollParser:
    """Parser for rent roll documents (Excel, CSV)"""

    def parse_rent_roll(self, file_path: str) -> RentRoll:
        """
        Parse rent roll document

        Args:
            file_path: Path to rent roll (XLS, XLSX, CSV)

        Returns:
            RentRoll object with all entries
        """
        logger.info(f"Parsing rent roll: {file_path}")

        # Read file based on extension
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        # Normalize column names
        df.columns = [col.lower().strip().replace(' ', '_') for col in df.columns]

        # Extract property info
        property_name = self._extract_property_name(df)
        property_address = self._extract_property_address(df)
        as_of_date = datetime.now().date()  # Could extract from document

        # Parse entries
        entries = []
        for _, row in df.iterrows():
            entry = self._parse_rent_roll_row(row)
            if entry:
                entries.append(entry)

        # Create rent roll
        rent_roll = RentRoll(
            property_name=property_name,
            property_address=property_address,
            as_of_date=as_of_date,
            entries=entries
        )

        # Calculate summary
        rent_roll.calculate_summary()

        logger.info(f"Parsed rent roll: {rent_roll.total_units} units, {rent_roll.occupancy_rate:.1%} occupancy")

        return rent_roll

    def _extract_property_name(self, df: pd.DataFrame) -> str:
        """Extract property name from dataframe"""
        # Check for property name in first few rows
        for col in df.columns:
            if 'property' in col and 'name' in col:
                return str(df[col].iloc[0])

        return "Unknown Property"

    def _extract_property_address(self, df: pd.DataFrame) -> str:
        """Extract property address from dataframe"""
        for col in df.columns:
            if 'address' in col:
                return str(df[col].iloc[0])

        return "Unknown Address"

    def _parse_rent_roll_row(self, row: pd.Series) -> Optional[RentRollEntry]:
        """Parse single rent roll row"""
        try:
            unit_number = str(row.get('unit', row.get('unit_number', '')))
            if not unit_number or unit_number == 'nan':
                return None

            tenant_name = str(row.get('tenant', row.get('tenant_name', '')))
            monthly_rent = float(row.get('rent', row.get('monthly_rent', 0)))

            status = str(row.get('status', 'occupied')).lower()
            if status == 'nan':
                status = 'occupied'

            entry = RentRollEntry(
                unit_number=unit_number,
                tenant_name=tenant_name,
                monthly_rent=monthly_rent,
                status=status
            )

            # Optional fields
            if 'lease_start' in row:
                entry.lease_start = self._parse_date_safe(row['lease_start'])
            if 'lease_end' in row:
                entry.lease_end = self._parse_date_safe(row['lease_end'])
            if 'security_deposit' in row:
                entry.security_deposit = float(row['security_deposit'])
            if 'bedrooms' in row:
                entry.bedrooms = int(row['bedrooms'])
            if 'bathrooms' in row:
                entry.bathrooms = float(row['bathrooms'])
            if 'sqft' in row or 'square_feet' in row:
                entry.sqft = int(row.get('sqft', row.get('square_feet', 0)))

            return entry

        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    def _parse_date_safe(self, date_val) -> Optional[date]:
        """Safely parse date value"""
        if pd.isna(date_val):
            return None
        if isinstance(date_val, date):
            return date_val
        if isinstance(date_val, str):
            try:
                return datetime.strptime(date_val, "%m/%d/%Y").date()
            except ValueError:
                return None
        return None


if __name__ == "__main__":
    # Test lease parser
    logging.basicConfig(level=logging.INFO)

    parser = LeaseParser()

    # Example usage
    print("Lease Parser initialized")
    print("To parse a lease: parser.parse_lease_document('path/to/lease.pdf')")

    rent_roll_parser = RentRollParser()
    print("Rent Roll Parser initialized")
    print("To parse a rent roll: rent_roll_parser.parse_rent_roll('path/to/rentroll.xlsx')")
