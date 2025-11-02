"""
Lender Fit Scoring System.

Matches properties and deals with appropriate lenders based on:
- Deal characteristics (LTV, DSCR, property type, location)
- Lender criteria (loan programs, underwriting requirements)
- Borrower qualifications (credit, experience, reserves)
- Optimal financing terms

Helps investors:
- Find best financing options quickly
- Avoid wasting time with unsuitable lenders
- Optimize deal structure for financing
- Understand financing constraints upfront
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class PropertyType(Enum):
    """Property types for lending."""
    RESIDENTIAL_1_4_UNIT = "Residential 1-4 Unit"
    MULTIFAMILY_5_PLUS = "Multifamily 5+ Units"
    COMMERCIAL = "Commercial"
    MIXED_USE = "Mixed Use"
    LAND = "Land"
    CONSTRUCTION = "Construction"


class LoanPurpose(Enum):
    """Loan purposes."""
    PURCHASE = "Purchase"
    REFINANCE = "Refinance"
    CASH_OUT_REFINANCE = "Cash-Out Refinance"
    REHAB = "Rehab"
    BRIDGE = "Bridge"
    CONSTRUCTION = "Construction"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class DealCharacteristics:
    """Deal/property characteristics for lender matching."""
    # Property details
    property_type: PropertyType
    property_value: float
    loan_amount: float

    # Location
    state: str
    city: str
    msa: Optional[str] = None

    # Financial metrics
    purchase_price: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_expenses: Optional[float] = None
    noi: Optional[float] = None  # Net Operating Income

    # Loan structure
    loan_purpose: LoanPurpose = LoanPurpose.PURCHASE
    down_payment: Optional[float] = None

    @property
    def ltv(self) -> float:
        """Loan-to-Value ratio."""
        if self.property_value > 0:
            return (self.loan_amount / self.property_value) * 100
        return 0

    @property
    def dscr(self) -> Optional[float]:
        """Debt Service Coverage Ratio."""
        if not self.monthly_rent or not self.loan_amount:
            return None

        # Estimate monthly payment at 7% for 30 years
        interest_rate = 0.07
        num_payments = 360
        monthly_rate = interest_rate / 12

        monthly_payment = self.loan_amount * (
            (monthly_rate * (1 + monthly_rate) ** num_payments) /
            ((1 + monthly_rate) ** num_payments - 1)
        )

        # Calculate NOI
        noi = self.monthly_rent - (self.monthly_expenses or 0)

        if monthly_payment > 0:
            return noi / monthly_payment
        return None


@dataclass
class BorrowerProfile:
    """Borrower qualifications."""
    # Credit
    credit_score: int

    # Experience
    num_properties_owned: int = 0
    years_experience: float = 0

    # Financials
    liquid_reserves: float = 0  # Months of reserves
    net_worth: Optional[float] = None
    annual_income: Optional[float] = None

    # Other
    has_recent_foreclosure: bool = False
    has_recent_bankruptcy: bool = False


@dataclass
class LenderCriteria:
    """Lender underwriting criteria and terms."""
    lender_id: str
    lender_name: str
    loan_program_name: str

    # Property types accepted
    accepted_property_types: List[PropertyType]

    # Loan purposes
    accepted_loan_purposes: List[LoanPurpose]

    # Geographic restrictions
    states_served: List[str]  # Empty = all states

    # LTV requirements
    max_ltv: float  # e.g., 80.0 for 80%
    min_ltv: float = 0

    # DSCR requirements
    min_dscr: Optional[float] = None  # e.g., 1.25 for 1.25x

    # Credit requirements
    min_credit_score: int = 620

    # Experience requirements
    min_properties_owned: int = 0
    min_years_experience: float = 0

    # Financial requirements
    min_reserves_months: float = 6.0

    # Loan size
    min_loan_amount: float = 50000
    max_loan_amount: float = 5000000

    # Terms
    interest_rate: float = 7.0  # Annual %
    loan_term_years: int = 30
    amortization_years: int = 30
    prepayment_penalty_years: int = 0

    # Fees
    origination_fee_percent: float = 1.0

    # Other
    allows_cash_out: bool = True
    allows_rehab: bool = False
    requires_appraisal: bool = True

    # Priority/ranking
    preferred_lender: bool = False  # Indicates relationship lender


@dataclass
class LenderMatch:
    """Lender match result with fit score."""
    lender: LenderCriteria
    fit_score: float  # 0-100, higher is better match
    qualified: bool  # Meets all hard requirements

    # Breakdown
    ltv_fit: float  # 0-100
    dscr_fit: float  # 0-100
    credit_fit: float  # 0-100
    experience_fit: float  # 0-100
    reserves_fit: float  # 0-100

    # Issues
    disqualification_reasons: List[str]
    warnings: List[str]

    # Terms
    estimated_rate: float
    estimated_monthly_payment: float
    estimated_origination_fee: float


# ============================================================================
# Lender Fit Scoring Engine
# ============================================================================

class LenderFitScorer:
    """
    Scores and ranks lenders based on deal fit.

    Matches deal characteristics and borrower profile against lender
    criteria to find best financing options.
    """

    def __init__(self, lenders: List[LenderCriteria]):
        """
        Initialize with list of lenders to score against.

        Args:
            lenders: List of lender criteria to evaluate
        """
        self.lenders = lenders
        logger.info(f"Initialized LenderFitScorer with {len(lenders)} lenders")

    def score_lenders(
        self,
        deal: DealCharacteristics,
        borrower: BorrowerProfile
    ) -> List[LenderMatch]:
        """
        Score all lenders for given deal and borrower.

        Returns list of LenderMatch objects sorted by fit score (best first).
        """
        logger.info(f"Scoring {len(self.lenders)} lenders for deal")

        matches = []
        for lender in self.lenders:
            match = self._score_single_lender(deal, borrower, lender)
            matches.append(match)

        # Sort by fit score (descending)
        matches.sort(key=lambda m: m.fit_score, reverse=True)

        # Log results
        qualified_count = sum(1 for m in matches if m.qualified)
        logger.info(f"Found {qualified_count}/{len(matches)} qualified lenders")
        if matches:
            logger.info(f"Best match: {matches[0].lender.lender_name} (score: {matches[0].fit_score:.1f})")

        return matches

    def _score_single_lender(
        self,
        deal: DealCharacteristics,
        borrower: BorrowerProfile,
        lender: LenderCriteria
    ) -> LenderMatch:
        """Score a single lender against deal and borrower."""

        disqualifications = []
        warnings = []

        # Initialize fit scores
        ltv_fit = 0
        dscr_fit = 0
        credit_fit = 0
        experience_fit = 0
        reserves_fit = 0

        # 1. Property type check (hard requirement)
        if deal.property_type not in lender.accepted_property_types:
            disqualifications.append(
                f"Property type {deal.property_type.value} not accepted"
            )

        # 2. Loan purpose check (hard requirement)
        if deal.loan_purpose not in lender.accepted_loan_purposes:
            disqualifications.append(
                f"Loan purpose {deal.loan_purpose.value} not accepted"
            )

        # 3. Geographic check (hard requirement)
        if lender.states_served and deal.state not in lender.states_served:
            disqualifications.append(
                f"State {deal.state} not in service area"
            )

        # 4. Loan size check (hard requirement)
        if deal.loan_amount < lender.min_loan_amount:
            disqualifications.append(
                f"Loan amount ${deal.loan_amount:,.0f} below minimum ${lender.min_loan_amount:,.0f}"
            )
        elif deal.loan_amount > lender.max_loan_amount:
            disqualifications.append(
                f"Loan amount ${deal.loan_amount:,.0f} above maximum ${lender.max_loan_amount:,.0f}"
            )

        # 5. LTV check and score
        deal_ltv = deal.ltv
        if deal_ltv > lender.max_ltv:
            disqualifications.append(
                f"LTV {deal_ltv:.1f}% exceeds maximum {lender.max_ltv:.1f}%"
            )
        elif deal_ltv < lender.min_ltv:
            disqualifications.append(
                f"LTV {deal_ltv:.1f}% below minimum {lender.min_ltv:.1f}%"
            )
        else:
            # Score based on how much room there is below max LTV
            # More room = better score
            ltv_utilization = deal_ltv / lender.max_ltv
            ltv_fit = (1 - ltv_utilization) * 100  # 0-100 scale

            if deal_ltv > lender.max_ltv * 0.95:
                warnings.append(f"LTV {deal_ltv:.1f}% close to maximum {lender.max_ltv:.1f}%")

        # 6. DSCR check and score
        if lender.min_dscr and deal.dscr is not None:
            if deal.dscr < lender.min_dscr:
                disqualifications.append(
                    f"DSCR {deal.dscr:.2f}x below minimum {lender.min_dscr:.2f}x"
                )
            else:
                # Score based on how much buffer above minimum
                dscr_buffer = deal.dscr - lender.min_dscr
                dscr_fit = min(dscr_buffer / 0.5, 1.0) * 100  # Cap at 100

                if deal.dscr < lender.min_dscr * 1.1:
                    warnings.append(f"DSCR {deal.dscr:.2f}x close to minimum {lender.min_dscr:.2f}x")
        elif lender.min_dscr and deal.dscr is None:
            warnings.append("DSCR cannot be calculated")
            dscr_fit = 50  # Neutral score
        else:
            dscr_fit = 100  # No DSCR requirement

        # 7. Credit score check and score
        if borrower.credit_score < lender.min_credit_score:
            disqualifications.append(
                f"Credit score {borrower.credit_score} below minimum {lender.min_credit_score}"
            )
        else:
            # Score based on buffer above minimum
            credit_buffer = borrower.credit_score - lender.min_credit_score
            credit_fit = min(credit_buffer / 100, 1.0) * 100  # Cap at 100

            if borrower.credit_score < lender.min_credit_score + 20:
                warnings.append(f"Credit score {borrower.credit_score} close to minimum {lender.min_credit_score}")

        # 8. Experience check and score
        if borrower.num_properties_owned < lender.min_properties_owned:
            disqualifications.append(
                f"Properties owned {borrower.num_properties_owned} below minimum {lender.min_properties_owned}"
            )
        elif borrower.years_experience < lender.min_years_experience:
            disqualifications.append(
                f"Experience {borrower.years_experience:.1f} years below minimum {lender.min_years_experience:.1f}"
            )
        else:
            # Score based on experience level
            property_score = min(borrower.num_properties_owned / 10, 1.0) * 50
            years_score = min(borrower.years_experience / 5, 1.0) * 50
            experience_fit = property_score + years_score

        # 9. Reserves check and score
        if borrower.liquid_reserves < lender.min_reserves_months:
            disqualifications.append(
                f"Reserves {borrower.liquid_reserves:.1f} months below minimum {lender.min_reserves_months:.1f}"
            )
        else:
            # Score based on buffer above minimum
            reserves_buffer = borrower.liquid_reserves - lender.min_reserves_months
            reserves_fit = min(reserves_buffer / 6, 1.0) * 100  # Cap at 100

            if borrower.liquid_reserves < lender.min_reserves_months * 1.2:
                warnings.append(f"Reserves {borrower.liquid_reserves:.1f} mo close to minimum {lender.min_reserves_months:.1f} mo")

        # 10. Other disqualifications
        if borrower.has_recent_foreclosure:
            disqualifications.append("Recent foreclosure")
        if borrower.has_recent_bankruptcy:
            disqualifications.append("Recent bankruptcy")

        # Calculate overall fit score
        qualified = len(disqualifications) == 0

        if qualified:
            # Weighted average of fit scores
            # LTV and DSCR are most important (30% each)
            # Credit is 20%, experience 10%, reserves 10%
            fit_score = (
                ltv_fit * 0.30 +
                dscr_fit * 0.30 +
                credit_fit * 0.20 +
                experience_fit * 0.10 +
                reserves_fit * 0.10
            )

            # Boost for preferred lenders
            if lender.preferred_lender:
                fit_score = min(fit_score * 1.1, 100)  # 10% boost, cap at 100
        else:
            fit_score = 0  # Not qualified

        # Calculate estimated terms
        estimated_rate = lender.interest_rate
        estimated_monthly_payment = self._calculate_monthly_payment(
            deal.loan_amount,
            estimated_rate,
            lender.amortization_years * 12
        )
        estimated_origination_fee = deal.loan_amount * (lender.origination_fee_percent / 100)

        return LenderMatch(
            lender=lender,
            fit_score=fit_score,
            qualified=qualified,
            ltv_fit=ltv_fit,
            dscr_fit=dscr_fit,
            credit_fit=credit_fit,
            experience_fit=experience_fit,
            reserves_fit=reserves_fit,
            disqualification_reasons=disqualifications,
            warnings=warnings,
            estimated_rate=estimated_rate,
            estimated_monthly_payment=estimated_monthly_payment,
            estimated_origination_fee=estimated_origination_fee
        )

    def _calculate_monthly_payment(
        self,
        loan_amount: float,
        annual_rate: float,
        num_payments: int
    ) -> float:
        """Calculate monthly mortgage payment."""
        if annual_rate == 0:
            return loan_amount / num_payments

        monthly_rate = annual_rate / 100 / 12
        payment = loan_amount * (
            (monthly_rate * (1 + monthly_rate) ** num_payments) /
            ((1 + monthly_rate) ** num_payments - 1)
        )
        return payment


# ============================================================================
# Sample Lender Database
# ============================================================================

def get_sample_lenders() -> List[LenderCriteria]:
    """Get sample lender database for testing."""
    return [
        # Conventional lender - strict but best rates
        LenderCriteria(
            lender_id="LEND-001",
            lender_name="Prime National Bank",
            loan_program_name="Conventional Investment Property",
            accepted_property_types=[
                PropertyType.RESIDENTIAL_1_4_UNIT,
                PropertyType.MULTIFAMILY_5_PLUS
            ],
            accepted_loan_purposes=[
                LoanPurpose.PURCHASE,
                LoanPurpose.REFINANCE,
                LoanPurpose.CASH_OUT_REFINANCE
            ],
            states_served=[],  # All states
            max_ltv=75.0,
            min_dscr=1.25,
            min_credit_score=700,
            min_properties_owned=2,
            min_years_experience=2.0,
            min_reserves_months=12.0,
            min_loan_amount=75000,
            max_loan_amount=2000000,
            interest_rate=6.5,
            loan_term_years=30,
            amortization_years=30,
            origination_fee_percent=0.75,
            preferred_lender=True
        ),

        # Portfolio lender - more flexible
        LenderCriteria(
            lender_id="LEND-002",
            lender_name="Investor Capital Group",
            loan_program_name="Portfolio Investment Loan",
            accepted_property_types=[
                PropertyType.RESIDENTIAL_1_4_UNIT,
                PropertyType.MULTIFAMILY_5_PLUS,
                PropertyType.COMMERCIAL,
                PropertyType.MIXED_USE
            ],
            accepted_loan_purposes=[
                LoanPurpose.PURCHASE,
                LoanPurpose.REFINANCE,
                LoanPurpose.CASH_OUT_REFINANCE,
                LoanPurpose.BRIDGE
            ],
            states_served=[],
            max_ltv=80.0,
            min_dscr=1.20,
            min_credit_score=660,
            min_properties_owned=1,
            min_years_experience=1.0,
            min_reserves_months=9.0,
            min_loan_amount=50000,
            max_loan_amount=3000000,
            interest_rate=7.25,
            loan_term_years=30,
            amortization_years=30,
            origination_fee_percent=1.0
        ),

        # DSCR lender - no income verification
        LenderCriteria(
            lender_id="LEND-003",
            lender_name="DSCR Lending Solutions",
            loan_program_name="No-Doc DSCR Loan",
            accepted_property_types=[
                PropertyType.RESIDENTIAL_1_4_UNIT,
                PropertyType.MULTIFAMILY_5_PLUS
            ],
            accepted_loan_purposes=[
                LoanPurpose.PURCHASE,
                LoanPurpose.REFINANCE,
                LoanPurpose.CASH_OUT_REFINANCE
            ],
            states_served=[],
            max_ltv=80.0,
            min_dscr=1.00,  # Lower DSCR requirement
            min_credit_score=640,
            min_properties_owned=0,  # First-time investors OK
            min_years_experience=0,
            min_reserves_months=6.0,
            min_loan_amount=100000,
            max_loan_amount=2500000,
            interest_rate=7.75,
            loan_term_years=30,
            amortization_years=30,
            origination_fee_percent=1.5
        ),

        # Hard money - very flexible, short-term
        LenderCriteria(
            lender_id="LEND-004",
            lender_name="Quick Close Capital",
            loan_program_name="Hard Money Bridge Loan",
            accepted_property_types=[
                PropertyType.RESIDENTIAL_1_4_UNIT,
                PropertyType.MULTIFAMILY_5_PLUS,
                PropertyType.COMMERCIAL
            ],
            accepted_loan_purposes=[
                LoanPurpose.PURCHASE,
                LoanPurpose.BRIDGE,
                LoanPurpose.REHAB
            ],
            states_served=[],
            max_ltv=70.0,
            min_dscr=None,  # No DSCR requirement
            min_credit_score=600,
            min_properties_owned=0,
            min_years_experience=0,
            min_reserves_months=3.0,
            min_loan_amount=50000,
            max_loan_amount=5000000,
            interest_rate=10.0,  # Higher rate
            loan_term_years=2,  # Short term
            amortization_years=30,
            origination_fee_percent=2.0,  # Higher fees
            allows_rehab=True
        )
    ]
