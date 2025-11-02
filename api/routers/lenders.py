"""
Lender Fit Scoring API Router.

Endpoints for matching deals with appropriate lenders.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging

from api.auth import get_current_user, TokenData
from api.rate_limit import rate_limit
from ml.lender_fit.lender_scoring import (
    LenderFitScorer,
    DealCharacteristics,
    BorrowerProfile,
    PropertyType,
    LoanPurpose,
    get_sample_lenders
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/lenders",
    tags=["Lender Fit Scoring"]
)

# Initialize scorer with sample lenders
# In production, this would load from database
sample_lenders = get_sample_lenders()
scorer = LenderFitScorer(lenders=sample_lenders)


# ============================================================================
# Request/Response Models
# ============================================================================

class DealRequest(BaseModel):
    """Deal characteristics."""
    property_type: str = Field(..., description="Property type")
    property_value: float = Field(..., gt=0)
    loan_amount: float = Field(..., gt=0)

    state: str = Field(..., description="State code (e.g., CA)")
    city: str
    msa: Optional[str] = None

    purchase_price: Optional[float] = None
    monthly_rent: Optional[float] = None
    monthly_expenses: Optional[float] = None
    noi: Optional[float] = None

    loan_purpose: str = Field("Purchase", description="Loan purpose")
    down_payment: Optional[float] = None


class BorrowerRequest(BaseModel):
    """Borrower profile."""
    credit_score: int = Field(..., ge=300, le=850)

    num_properties_owned: int = Field(0, ge=0)
    years_experience: float = Field(0, ge=0)

    liquid_reserves: float = Field(0, ge=0, description="Months of reserves")
    net_worth: Optional[float] = None
    annual_income: Optional[float] = None

    has_recent_foreclosure: bool = False
    has_recent_bankruptcy: bool = False


class LenderFitRequest(BaseModel):
    """Complete lender fit request."""
    deal: DealRequest
    borrower: BorrowerRequest


class LenderMatchResponse(BaseModel):
    """Lender match result."""
    lender_id: str
    lender_name: str
    loan_program_name: str

    fit_score: float
    qualified: bool

    # Fit breakdown
    ltv_fit: float
    dscr_fit: float
    credit_fit: float
    experience_fit: float
    reserves_fit: float

    # Issues
    disqualification_reasons: List[str]
    warnings: List[str]

    # Terms
    estimated_rate: float
    estimated_monthly_payment: float
    estimated_origination_fee: float
    loan_term_years: int
    max_ltv: float
    min_dscr: Optional[float]


class LenderFitResponse(BaseModel):
    """Complete lender fit response."""
    # Deal summary
    deal_ltv: float
    deal_dscr: Optional[float]

    # Results
    total_lenders_evaluated: int
    qualified_lenders: int
    best_match: Optional[LenderMatchResponse]
    all_matches: List[LenderMatchResponse]

    # Metadata
    scored_at: datetime


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/score",
    response_model=LenderFitResponse,
    status_code=status.HTTP_200_OK,
    summary="Score lender fit",
    description="Match deal with appropriate lenders based on fit score"
)
@rate_limit(requests_per_minute=30)
async def score_lender_fit(
    request: LenderFitRequest,
    user: TokenData = Depends(get_current_user)
):
    """
    Score lender fit for a deal and borrower.

    Evaluates all available lenders against deal characteristics and
    borrower qualifications, returning ranked list by fit score.

    **Scoring Factors (0-100):**
    - LTV fit (30%): Lower LTV relative to max = better
    - DSCR fit (30%): Higher DSCR relative to min = better
    - Credit fit (20%): Higher credit score = better
    - Experience fit (10%): More properties/experience = better
    - Reserves fit (10%): More reserves = better

    **Hard Requirements:**
    - Property type must match
    - Loan purpose must match
    - State must be in service area
    - Loan size within limits
    - LTV below maximum
    - DSCR above minimum (if required)
    - Credit score above minimum
    - Experience meets requirements
    - Reserves meet requirements

    **Use Cases:**
    - Find best financing for acquisition
    - Pre-qualify deals before making offers
    - Optimize deal structure for financing
    - Understand financing constraints
    - Compare lender terms side-by-side
    """
    logger.info(f"Lender fit scoring request from user {user.user_id}")

    try:
        # Parse property type
        try:
            property_type = PropertyType[request.deal.property_type.upper().replace(" ", "_").replace("-", "_")]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid property type: {request.deal.property_type}"
            )

        # Parse loan purpose
        try:
            loan_purpose = LoanPurpose[request.deal.loan_purpose.upper().replace(" ", "_").replace("-", "_")]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid loan purpose: {request.deal.loan_purpose}"
            )

        # Create deal characteristics
        deal = DealCharacteristics(
            property_type=property_type,
            property_value=request.deal.property_value,
            loan_amount=request.deal.loan_amount,
            state=request.deal.state,
            city=request.deal.city,
            msa=request.deal.msa,
            purchase_price=request.deal.purchase_price,
            monthly_rent=request.deal.monthly_rent,
            monthly_expenses=request.deal.monthly_expenses,
            noi=request.deal.noi,
            loan_purpose=loan_purpose,
            down_payment=request.deal.down_payment
        )

        # Create borrower profile
        borrower = BorrowerProfile(
            credit_score=request.borrower.credit_score,
            num_properties_owned=request.borrower.num_properties_owned,
            years_experience=request.borrower.years_experience,
            liquid_reserves=request.borrower.liquid_reserves,
            net_worth=request.borrower.net_worth,
            annual_income=request.borrower.annual_income,
            has_recent_foreclosure=request.borrower.has_recent_foreclosure,
            has_recent_bankruptcy=request.borrower.has_recent_bankruptcy
        )

        # Score lenders
        matches = scorer.score_lenders(deal, borrower)

        # Convert to response models
        match_responses = []
        for match in matches:
            match_responses.append(LenderMatchResponse(
                lender_id=match.lender.lender_id,
                lender_name=match.lender.lender_name,
                loan_program_name=match.lender.loan_program_name,
                fit_score=match.fit_score,
                qualified=match.qualified,
                ltv_fit=match.ltv_fit,
                dscr_fit=match.dscr_fit,
                credit_fit=match.credit_fit,
                experience_fit=match.experience_fit,
                reserves_fit=match.reserves_fit,
                disqualification_reasons=match.disqualification_reasons,
                warnings=match.warnings,
                estimated_rate=match.estimated_rate,
                estimated_monthly_payment=match.estimated_monthly_payment,
                estimated_origination_fee=match.estimated_origination_fee,
                loan_term_years=match.lender.loan_term_years,
                max_ltv=match.lender.max_ltv,
                min_dscr=match.lender.min_dscr
            ))

        qualified_count = sum(1 for m in match_responses if m.qualified)
        best_match = match_responses[0] if match_responses and match_responses[0].qualified else None

        logger.info(
            f"Scored {len(matches)} lenders: {qualified_count} qualified, "
            f"best: {best_match.lender_name if best_match else 'None'}"
        )

        return LenderFitResponse(
            deal_ltv=deal.ltv,
            deal_dscr=deal.dscr,
            total_lenders_evaluated=len(matches),
            qualified_lenders=qualified_count,
            best_match=best_match,
            all_matches=match_responses,
            scored_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lender fit scoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoring failed: {str(e)}"
        )


@router.get(
    "/programs",
    summary="List available loan programs",
    description="Get list of all available lenders and loan programs"
)
@rate_limit(requests_per_minute=60)
async def list_loan_programs(
    user: TokenData = Depends(get_current_user)
):
    """
    List all available lenders and loan programs.

    Returns details on all lenders in the system for reference.
    """
    logger.info(f"Loan programs list request from user {user.user_id}")

    programs = []
    for lender in sample_lenders:
        programs.append({
            "lender_id": lender.lender_id,
            "lender_name": lender.lender_name,
            "loan_program_name": lender.loan_program_name,
            "property_types": [pt.value for pt in lender.accepted_property_types],
            "loan_purposes": [lp.value for lp in lender.accepted_loan_purposes],
            "max_ltv": lender.max_ltv,
            "min_dscr": lender.min_dscr,
            "min_credit_score": lender.min_credit_score,
            "interest_rate": lender.interest_rate,
            "loan_term_years": lender.loan_term_years,
            "min_loan_amount": lender.min_loan_amount,
            "max_loan_amount": lender.max_loan_amount,
            "preferred_lender": lender.preferred_lender
        })

    return {
        "total_programs": len(programs),
        "programs": programs
    }


@router.get(
    "/requirements/{lender_id}",
    summary="Get lender requirements",
    description="Get detailed requirements for a specific lender"
)
@rate_limit(requests_per_minute=60)
async def get_lender_requirements(
    lender_id: str,
    user: TokenData = Depends(get_current_user)
):
    """
    Get detailed requirements for a specific lender.

    Returns complete underwriting criteria and terms.
    """
    logger.info(f"Lender requirements request for {lender_id} from user {user.user_id}")

    # Find lender
    lender = next((l for l in sample_lenders if l.lender_id == lender_id), None)

    if not lender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lender {lender_id} not found"
        )

    return {
        "lender_id": lender.lender_id,
        "lender_name": lender.lender_name,
        "loan_program_name": lender.loan_program_name,
        "requirements": {
            "property_types": [pt.value for pt in lender.accepted_property_types],
            "loan_purposes": [lp.value for lp in lender.accepted_loan_purposes],
            "states_served": lender.states_served if lender.states_served else "All states",
            "ltv": {
                "min": lender.min_ltv,
                "max": lender.max_ltv
            },
            "dscr": {
                "min": lender.min_dscr
            },
            "credit_score": {
                "min": lender.min_credit_score
            },
            "experience": {
                "min_properties_owned": lender.min_properties_owned,
                "min_years_experience": lender.min_years_experience
            },
            "reserves": {
                "min_months": lender.min_reserves_months
            },
            "loan_size": {
                "min": lender.min_loan_amount,
                "max": lender.max_loan_amount
            }
        },
        "terms": {
            "interest_rate": lender.interest_rate,
            "loan_term_years": lender.loan_term_years,
            "amortization_years": lender.amortization_years,
            "origination_fee_percent": lender.origination_fee_percent,
            "prepayment_penalty_years": lender.prepayment_penalty_years
        },
        "features": {
            "allows_cash_out": lender.allows_cash_out,
            "allows_rehab": lender.allows_rehab,
            "requires_appraisal": lender.requires_appraisal,
            "preferred_lender": lender.preferred_lender
        }
    }
