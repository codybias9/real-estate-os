"""
Portfolio & Outcomes Router
Deal Economics, Investor Readiness, Template Leaderboards
What leaders care about: outcomes and performance
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime

from api.database import get_db
from api import schemas
from db.models import (
    Property, Deal, DealScenario, DealStatus, Template,
    Communication, DealRoom, InvestorReadinessLevel
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio & Outcomes"])

# ============================================================================
# DEAL ECONOMICS PANEL
# ============================================================================

@router.post("/deals", response_model=schemas.DealResponse, status_code=201)
def create_deal(
    deal_data: schemas.DealCreate,
    db: Session = Depends(get_db)
):
    """
    Create a deal with economics tracking

    Calculates:
    - Expected margin
    - Probability of close
    - Expected Value (EV) = margin × probability
    - Top 2 drivers affecting EV
    """
    # Get property
    property = db.query(Property).filter(Property.id == deal_data.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Calculate expected margin
    expected_margin = 0.0
    if deal_data.assignment_fee:
        expected_margin = deal_data.assignment_fee
    elif deal_data.arv and deal_data.offer_price and deal_data.repair_cost:
        expected_margin = deal_data.arv - deal_data.offer_price - deal_data.repair_cost

    # Use property probability or default to 0.5
    probability = deal_data.probability_of_close or property.probability_of_close or 0.5

    # Calculate EV
    expected_value = expected_margin * probability

    # Determine top EV drivers
    ev_drivers = []

    if deal_data.arv:
        ev_drivers.append({
            "factor": "ARV",
            "value": deal_data.arv,
            "impact": "high",
            "explanation": f"ARV of ${deal_data.arv:,.0f} drives potential upside"
        })

    if deal_data.repair_cost:
        ev_drivers.append({
            "factor": "Repair Costs",
            "value": deal_data.repair_cost,
            "impact": "high",
            "explanation": f"${deal_data.repair_cost:,.0f} in repairs reduces margin"
        })

    if probability < 0.6:
        ev_drivers.append({
            "factor": "Probability",
            "value": probability,
            "impact": "medium",
            "explanation": f"{probability*100:.0f}% probability reduces expected value"
        })

    # Create deal
    deal = Deal(
        property_id=deal_data.property_id,
        offer_price=deal_data.offer_price,
        arv=deal_data.arv,
        repair_cost=deal_data.repair_cost,
        assignment_fee=deal_data.assignment_fee,
        expected_margin=expected_margin,
        probability_of_close=probability,
        expected_value=expected_value,
        ev_drivers=ev_drivers,
        investor_id=deal_data.investor_id,
        notes=deal_data.notes,
        status=DealStatus.PROPOSED,
        proposed_at=datetime.utcnow()
    )

    db.add(deal)
    db.flush()

    # Update property
    property.expected_value = expected_value
    property.probability_of_close = probability

    db.commit()
    db.refresh(deal)

    return deal

@router.get("/deals/{deal_id}", response_model=schemas.DealResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """
    Get deal with full economics
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return deal

@router.patch("/deals/{deal_id}", response_model=schemas.DealResponse)
def update_deal(
    deal_id: int,
    deal_update: schemas.DealUpdate,
    db: Session = Depends(get_db)
):
    """
    Update deal economics

    Recalculates EV when parameters change
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Apply updates
    update_data = deal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deal, field, value)

    # Recalculate margin and EV if financials changed
    if any(f in update_data for f in ["offer_price", "arv", "repair_cost", "assignment_fee", "probability_of_close"]):
        if deal.assignment_fee:
            deal.expected_margin = deal.assignment_fee
        elif deal.arv and deal.offer_price and deal.repair_cost:
            deal.expected_margin = deal.arv - deal.offer_price - deal.repair_cost

        if deal.expected_margin and deal.probability_of_close:
            deal.expected_value = deal.expected_margin * deal.probability_of_close

    deal.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(deal)

    return deal

# ============================================================================
# DEAL SCENARIOS (WHAT-IF ANALYSIS)
# ============================================================================

@router.post("/deals/{deal_id}/scenarios", response_model=schemas.DealScenarioResponse, status_code=201)
def create_deal_scenario(
    deal_id: int,
    scenario_data: schemas.DealScenarioCreate,
    db: Session = Depends(get_db)
):
    """
    Create a what-if scenario for a deal

    Example scenarios:
    - "What if we offer $10k more?"
    - "What if repairs are 20% higher?"
    - "What if we close in 14 days vs 30?"

    Shows how parameters affect:
    - Expected margin
    - Probability of close
    - Expected value
    """
    # Get deal
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Use scenario values or fall back to deal values
    offer_price = scenario_data.offer_price or deal.offer_price
    arv = scenario_data.arv or deal.arv
    repair_cost = scenario_data.repair_cost or deal.repair_cost

    # Calculate scenario results
    expected_margin = arv - offer_price - repair_cost if all([arv, offer_price, repair_cost]) else 0

    # Adjust probability based on scenario changes
    probability = deal.probability_of_close or 0.5

    # Simple heuristics (in production, use ML model):
    if scenario_data.offer_price and deal.offer_price:
        price_increase_pct = (scenario_data.offer_price - deal.offer_price) / deal.offer_price
        # Higher offer = higher probability (up to 10%)
        probability = min(1.0, probability + (price_increase_pct * 0.1))

    if scenario_data.days_to_close:
        # Faster close = slightly lower probability
        if scenario_data.days_to_close < 30:
            probability *= 0.95

    expected_value = expected_margin * probability

    # Generate impact summary
    margin_diff = expected_margin - (deal.expected_margin or 0)
    ev_diff = expected_value - (deal.expected_value or 0)

    impact_summary = f"""
Scenario Impact:
- Margin: ${expected_margin:,.0f} ({'+' if margin_diff > 0 else ''}{margin_diff:,.0f})
- Probability: {probability*100:.1f}% ({'+' if probability > (deal.probability_of_close or 0) else ''}{(probability - (deal.probability_of_close or 0))*100:.1f}%)
- Expected Value: ${expected_value:,.0f} ({'+' if ev_diff > 0 else ''}{ev_diff:,.0f})
"""

    # Create scenario
    scenario = DealScenario(
        deal_id=deal_id,
        name=scenario_data.name,
        offer_price=offer_price,
        arv=arv,
        repair_cost=repair_cost,
        days_to_close=scenario_data.days_to_close,
        expected_margin=expected_margin,
        probability_of_close=probability,
        expected_value=expected_value,
        impact_summary=impact_summary.strip()
    )

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return scenario

@router.get("/deals/{deal_id}/scenarios", response_model=List[schemas.DealScenarioResponse])
def list_deal_scenarios(deal_id: int, db: Session = Depends(get_db)):
    """
    List all scenarios for a deal
    """
    scenarios = (
        db.query(DealScenario)
        .filter(DealScenario.deal_id == deal_id)
        .order_by(desc(DealScenario.expected_value))
        .all()
    )

    return scenarios

# ============================================================================
# INVESTOR READINESS SCORE
# ============================================================================

@router.get("/properties/{property_id}/investor-readiness")
def get_investor_readiness(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate investor readiness score

    Combines:
    - Memo freshness
    - Comps completeness
    - Disclosure checklist
    - Recent activity

    Returns:
    - RED: Missing critical items
    - YELLOW: Mostly ready, minor items
    - GREEN: Ready to share

    Unlocks "Share Packet" button only when GREEN
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Check readiness factors
    factors = {
        "has_memo": bool(property.memo_url),
        "memo_fresh": False,
        "has_packet": bool(property.packet_url),
        "has_valuation": bool(property.arv and property.market_value_estimate),
        "recent_activity": bool(property.last_contact_date),
        "compliance_clear": not property.is_on_dnc and not property.has_opted_out
    }

    # Check memo freshness (within 30 days)
    if property.memo_generated_at:
        days_old = (datetime.utcnow() - property.memo_generated_at).days
        factors["memo_fresh"] = days_old <= 30

    # Calculate readiness level
    critical_items = ["has_memo", "has_valuation", "compliance_clear"]
    nice_to_have = ["memo_fresh", "has_packet", "recent_activity"]

    critical_complete = all(factors[key] for key in critical_items)
    nice_to_have_count = sum(factors[key] for key in nice_to_have)

    if not critical_complete:
        readiness_level = InvestorReadinessLevel.RED
    elif nice_to_have_count >= 2:
        readiness_level = InvestorReadinessLevel.GREEN
    else:
        readiness_level = InvestorReadinessLevel.YELLOW

    # Missing items
    missing_items = [key for key, value in factors.items() if not value]

    return {
        "property_id": property_id,
        "readiness_level": readiness_level.value,
        "factors": factors,
        "missing_items": missing_items,
        "can_share": readiness_level == InvestorReadinessLevel.GREEN
    }

# ============================================================================
# TEMPLATE LEADERBOARDS
# ============================================================================

@router.get("/template-performance", response_model=List[schemas.TemplatePerformance])
def get_template_leaderboard(
    team_id: int,
    type: Optional[schemas.CommunicationTypeEnum] = Query(None),
    stage: Optional[schemas.PropertyStageEnum] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Template Leaderboards: Rank by performance

    Shows templates ranked by:
    - Reply rate (most important)
    - Open rate
    - Meeting conversion rate

    Supports champion vs challenger A/B testing

    KPI: Uplift in reply rate from using top performers
    """
    query = db.query(Template).filter(
        Template.team_id == team_id,
        Template.is_active == True,
        Template.times_used >= 10  # Minimum usage for statistical significance
    )

    if type:
        query = query.filter(Template.type == type.value)

    if stage:
        query = query.filter(Template.applicable_stages.contains([stage.value]))

    # Order by reply rate (primary), then open rate (secondary)
    templates = (
        query
        .order_by(
            desc(Template.reply_rate).nullslast(),
            desc(Template.open_rate).nullslast(),
            desc(Template.meeting_rate).nullslast()
        )
        .limit(limit)
        .all()
    )

    # Build leaderboard response
    leaderboard = []
    for rank, template in enumerate(templates, start=1):
        leaderboard.append({
            "template_id": template.id,
            "template_name": template.name,
            "times_used": template.times_used,
            "open_rate": template.open_rate or 0.0,
            "reply_rate": template.reply_rate or 0.0,
            "meeting_rate": template.meeting_rate or 0.0,
            "rank": rank
        })

    return leaderboard

@router.post("/templates/{template_id}/track-performance")
def track_template_performance(
    template_id: int,
    opened: bool = False,
    replied: bool = False,
    meeting_booked: bool = False,
    db: Session = Depends(get_db)
):
    """
    Track template performance metrics

    Called after communication events:
    - Email opened
    - Reply received
    - Meeting booked

    Recalculates rates incrementally
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all communications using this template
    total_uses = template.times_used or 0

    if total_uses == 0:
        return {"status": "no_uses_yet"}

    # Count events from communications
    stats = (
        db.query(
            func.count(Communication.opened_at).label("opens"),
            func.count(Communication.replied_at).label("replies"),
            func.count(Communication.metadata["meeting_booked"]).label("meetings")
        )
        .filter(Communication.template_id == template_id)
        .first()
    )

    # Recalculate rates
    template.open_rate = stats.opens / total_uses if total_uses > 0 else 0.0
    template.reply_rate = stats.replies / total_uses if total_uses > 0 else 0.0
    template.meeting_rate = stats.meetings / total_uses if total_uses > 0 else 0.0

    db.commit()

    return {
        "template_id": template_id,
        "times_used": total_uses,
        "open_rate": template.open_rate,
        "reply_rate": template.reply_rate,
        "meeting_rate": template.meeting_rate
    }
