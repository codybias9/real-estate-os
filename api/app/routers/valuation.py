"""Valuation Router
DCF-based valuation endpoints for multi-family and commercial properties
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from ..database import get_db
from ..auth.hybrid_dependencies import get_current_user
from ..auth.models import User
import sys
sys.path.append('/home/user/real-estate-os')
from ml.valuation.dcf_engine import DCFEngine, DCFAssumptions, DCFResult
from ml.valuation.mf_valuation import MFValuationEngine, value_mf_property_simple
from ml.valuation.cre_valuation import CREValuationEngine, value_cre_property_simple

router = APIRouter(
    prefix="/valuation",
    tags=["valuation"]
)


# ============================================================================
# Models
# ============================================================================

class AssetType(str, Enum):
    """Asset types for valuation"""
    MULTI_FAMILY = "multi_family"
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    FLEX = "flex"


class ValuationMethod(str, Enum):
    """Valuation methods"""
    DIRECT_CAP = "direct_cap"
    DCF_MF = "dcf_mf"
    DCF_CRE = "dcf_cre"
    COMP_CRITIC = "comp_critic"


class ValuationRequest(BaseModel):
    """Request for property valuation"""
    property_id: UUID
    valuation_method: ValuationMethod = ValuationMethod.DIRECT_CAP

    # DCF parameters
    holding_period_years: int = Field(default=10, ge=1, le=30)
    exit_cap_rate: float = Field(default=0.055, ge=0.01, le=0.20)
    discount_rate: float = Field(default=0.12, ge=0.05, le=0.30)
    loan_to_value: float = Field(default=0.70, ge=0.0, le=0.95)
    interest_rate: float = Field(default=0.055, ge=0.01, le=0.15)
    amortization_years: int = Field(default=30, ge=10, le=30)


class UnitMixInput(BaseModel):
    """Unit mix for MF properties"""
    unit_type: str
    unit_count: int
    avg_sf_per_unit: float
    market_rent: float
    current_avg_rent: Optional[float] = None
    occupied_count: Optional[int] = None


class LeaseInput(BaseModel):
    """Lease for CRE properties"""
    lease_id: str
    tenant_name: str
    suite_number: Optional[str] = None
    leased_sf: float
    lease_start_date: str
    lease_end_date: str
    lease_term_months: int
    base_rent_psf_annual: float
    annual_escalation_pct: float = 0.03
    credit_rating: str = "unrated"
    renewal_probability: float = 0.65


class MFValuationRequest(BaseModel):
    """Multi-family valuation request with unit mix"""
    property_id: str
    property_name: Optional[str] = None
    address: Optional[str] = None

    # Physical
    total_units: int
    total_sf: int
    year_built: int

    # Unit mix
    unit_mix: List[UnitMixInput]

    # Financials
    current_monthly_rent_roll: float = 0.0
    annual_other_income: float = 0.0
    current_physical_vacancy_rate: float = 0.05
    economic_vacancy_rate: float = 0.03
    annual_opex: float = 0.0
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0

    # Market
    market: str = "unknown"
    market_rent_growth: float = 0.03

    # DCF parameters
    holding_period_years: int = 10
    exit_cap_rate: float = 0.055


class CREValuationRequest(BaseModel):
    """Commercial real estate valuation request with leases"""
    property_id: str
    property_name: Optional[str] = None
    address: Optional[str] = None

    # Physical
    property_type: str  # office, retail, industrial
    total_sf: float
    year_built: int

    # Leasing
    leases: List[LeaseInput]
    occupied_sf: float
    vacant_sf: float

    # Financials
    annual_opex_psf: float = 8.0
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0

    # Market
    market: str = "unknown"
    market_rent_psf: float = 25.0
    market_vacancy_rate: float = 0.10
    market_rent_growth: float = 0.025

    # DCF parameters
    holding_period_years: int = 10
    exit_cap_rate: float = 0.065


class ValuationResult(BaseModel):
    """Valuation result"""
    property_id: str
    valuation_date: str
    valuation_method: str

    # Valuation
    direct_cap_value: float
    npv: Optional[float] = None
    irr: Optional[float] = None
    equity_multiple: Optional[float] = None

    # NOI
    stabilized_noi: float

    # Debt metrics
    avg_dscr: Optional[float] = None
    min_dscr: Optional[float] = None
    loan_amount: Optional[float] = None

    # Cash flows
    total_equity_invested: Optional[float] = None
    total_cash_distributed: Optional[float] = None

    # Parameters
    holding_period_years: Optional[int] = None
    exit_cap_rate: Optional[float] = None


class RentRollAnalysis(BaseModel):
    """Rent roll analysis result"""
    total_units_or_sf: float
    occupied_units_or_sf: float
    vacant_units_or_sf: float
    occupancy_rate: float
    avg_in_place_rent: float
    avg_market_rent: float
    loss_to_lease_pct: float
    wale_years: Optional[float] = None  # CRE only
    rollover_risk_pct: Optional[float] = None  # CRE only


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/mf/value", response_model=ValuationResult)
async def value_mf_property(
    request: MFValuationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Value multi-family property using DCF

    Args:
        request: MF property data with unit mix
        user: Current authenticated user
        db: Database session

    Returns:
        Valuation result with NPV, IRR, cash flows
    """

    # Convert request to dict for valuation engine
    property_data = {
        "property_id": request.property_id,
        "property_name": request.property_name or "Unknown",
        "address": request.address or "",
        "total_units": request.total_units,
        "total_sf": request.total_sf,
        "year_built": request.year_built,
        "unit_mix": [unit.dict() for unit in request.unit_mix],
        "current_monthly_rent_roll": request.current_monthly_rent_roll,
        "annual_other_income": request.annual_other_income,
        "current_physical_vacancy_rate": request.current_physical_vacancy_rate,
        "economic_vacancy_rate": request.economic_vacancy_rate,
        "annual_opex": request.annual_opex,
        "annual_property_tax": request.annual_property_tax,
        "annual_insurance": request.annual_insurance,
        "market": request.market,
        "market_rent_growth": request.market_rent_growth
    }

    # Run valuation
    result = value_mf_property_simple(
        property_data=property_data,
        holding_period_years=request.holding_period_years,
        exit_cap_rate=request.exit_cap_rate
    )

    return ValuationResult(
        property_id=result["property_id"],
        valuation_date=result["valuation_date"],
        valuation_method=result["valuation_method"],
        direct_cap_value=result["direct_cap_value"],
        npv=result["npv"],
        irr=result["irr"],
        equity_multiple=result["equity_multiple"],
        stabilized_noi=result["stabilized_noi"],
        avg_dscr=result["avg_dscr"],
        min_dscr=result["min_dscr"],
        total_equity_invested=result["total_equity_invested"],
        total_cash_distributed=result["total_cash_distributed"],
        holding_period_years=result["holding_period_years"],
        exit_cap_rate=result["exit_cap_rate"]
    )


@router.post("/cre/value", response_model=ValuationResult)
async def value_cre_property(
    request: CREValuationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Value commercial property using DCF with lease rollover

    Args:
        request: CRE property data with leases
        user: Current authenticated user
        db: Database session

    Returns:
        Valuation result with NPV, IRR, TI/LC reserves
    """

    # Convert request to dict for valuation engine
    property_data = {
        "property_id": request.property_id,
        "property_name": request.property_name or "Unknown",
        "address": request.address or "",
        "property_type": request.property_type,
        "total_sf": request.total_sf,
        "year_built": request.year_built,
        "leases": [lease.dict() for lease in request.leases],
        "occupied_sf": request.occupied_sf,
        "vacant_sf": request.vacant_sf,
        "annual_opex_psf": request.annual_opex_psf,
        "annual_property_tax": request.annual_property_tax,
        "annual_insurance": request.annual_insurance,
        "market": request.market,
        "market_rent_psf": request.market_rent_psf,
        "market_vacancy_rate": request.market_vacancy_rate,
        "market_rent_growth": request.market_rent_growth
    }

    # Run valuation
    result = value_cre_property_simple(
        property_data=property_data,
        holding_period_years=request.holding_period_years,
        exit_cap_rate=request.exit_cap_rate
    )

    return ValuationResult(
        property_id=result["property_id"],
        valuation_date=result["valuation_date"],
        valuation_method=result["valuation_method"],
        direct_cap_value=result["direct_cap_value"],
        npv=result["npv"],
        irr=result["irr"],
        equity_multiple=result["equity_multiple"],
        stabilized_noi=result["stabilized_noi"],
        avg_dscr=result["avg_dscr"],
        min_dscr=result["min_dscr"],
        total_equity_invested=result["total_equity_invested"],
        total_cash_distributed=result["total_cash_distributed"],
        holding_period_years=result["holding_period_years"],
        exit_cap_rate=result["exit_cap_rate"]
    )


@router.get("/mf/{property_id}/rent-roll", response_model=RentRollAnalysis)
async def analyze_mf_rent_roll(
    property_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze multi-family rent roll

    Returns:
        Rent roll analysis with occupancy, loss-to-lease, etc.
    """

    # TODO: Load property from database
    # For now, return example response

    raise HTTPException(
        status_code=501,
        detail="Rent roll analysis requires property data from database"
    )


@router.get("/cre/{property_id}/rent-roll", response_model=RentRollAnalysis)
async def analyze_cre_rent_roll(
    property_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze commercial rent roll

    Returns:
        Rent roll analysis with WALE, rollover risk, tenant concentration
    """

    # TODO: Load property from database
    # For now, return example response

    raise HTTPException(
        status_code=501,
        detail="Rent roll analysis requires property data from database"
    )


@router.get("/cre/{property_id}/lease-rollover")
async def project_lease_rollover(
    property_id: str,
    projection_years: int = Query(default=10, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Project lease expirations and rollover costs

    Args:
        property_id: Property ID
        projection_years: Years to project
        user: Current user
        db: Database session

    Returns:
        DataFrame with rollover schedule and TI/LC costs
    """

    # TODO: Load property from database and project rollover

    raise HTTPException(
        status_code=501,
        detail="Lease rollover projection requires property data from database"
    )


@router.get("/methods")
async def list_valuation_methods():
    """List available valuation methods

    Returns:
        List of valuation methods with descriptions
    """

    methods = [
        {
            "method": "direct_cap",
            "name": "Direct Capitalization",
            "description": "NOI / Cap Rate - simple income approach",
            "applicable_to": ["all"]
        },
        {
            "method": "dcf_mf",
            "name": "Multi-Family DCF",
            "description": "10-year DCF with unit mix and rent growth",
            "applicable_to": ["multi_family"]
        },
        {
            "method": "dcf_cre",
            "name": "Commercial DCF",
            "description": "10-year DCF with lease rollover and TI/LC reserves",
            "applicable_to": ["office", "retail", "industrial", "flex"]
        },
        {
            "method": "comp_critic",
            "name": "Comp-Critic Valuation",
            "description": "3-stage comparable selection with hedonic adjustment",
            "applicable_to": ["single_family", "condo"]
        }
    ]

    return {"methods": methods}
