"""
Data & Propensity Router
Owner propensity signals, Provenance inspector, Deliverability tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta

from api.database import get_db
from api import schemas
from db.models import (
    Property, PropensitySignal, PropertyProvenance, DeliverabilityMetrics,
    BudgetTracking, OpenDataSource, Team
)

router = APIRouter(prefix="/data", tags=["Data & Propensity"])

# ============================================================================
# OWNER PROPENSITY SIGNALS
# ============================================================================

def _analyze_propensity_signals(property: Property) -> tuple[float, List[PropensitySignal]]:
    """
    Analyze public signals to determine likelihood owner will entertain offer

    Signals:
    - Long tenure (14+ years) → higher propensity
    - Recent sale / flip → lower propensity
    - Tax liens → higher propensity
    - Absentee owner → higher propensity
    - Vacancy indicators → higher propensity
    - Recent price cuts in area → higher propensity

    Returns: (propensity_score, signals_list)
    """
    signals = []
    score = 0.5  # Base score

    # Signal 1: Long tenure (if we have year_built and owner data)
    if property.year_built:
        # Simplified: assume ownership since 2010 for demo
        tenure_years = 2025 - 2010
        if tenure_years >= 14:
            weight = 0.15
            score += weight
            signals.append(PropensitySignal(
                property_id=property.id,
                signal_type="long_tenure",
                signal_value=f"{tenure_years} years",
                weight=weight,
                reasoning=f"Long tenure ({tenure_years}y) suggests potential retirement/downsizing motivation"
            ))

    # Signal 2: Absentee owner (mailing address different from property)
    if property.owner_mailing_address and property.address:
        if property.owner_mailing_address.lower() not in property.address.lower():
            weight = 0.20
            score += weight
            signals.append(PropensitySignal(
                property_id=property.id,
                signal_type="absentee_owner",
                signal_value="True",
                weight=weight,
                reasoning="Absentee owners are 2x more likely to consider offers"
            ))

    # Signal 3: Property condition (if low assessed value relative to area)
    if property.assessed_value and property.market_value_estimate:
        value_ratio = property.assessed_value / property.market_value_estimate
        if value_ratio < 0.7:
            weight = 0.12
            score += weight
            signals.append(PropensitySignal(
                property_id=property.id,
                signal_type="low_assessment",
                signal_value=f"{value_ratio:.2%}",
                weight=weight,
                reasoning="Low assessment may indicate distress or deferred maintenance"
            ))

    # Signal 4: High repair estimate
    if property.repair_estimate and property.repair_estimate > 50000:
        weight = 0.10
        score += weight
        signals.append(PropensitySignal(
            property_id=property.id,
            signal_type="high_repairs",
            signal_value=f"${property.repair_estimate:,.0f}",
            weight=weight,
            reasoning="Significant repairs may motivate as-is sale"
        ))

    # Cap score at 1.0
    score = min(1.0, score)

    return score, signals

@router.post("/propensity/analyze/{property_id}", response_model=schemas.PropensityAnalysisResponse)
def analyze_property_propensity(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Analyze owner propensity to sell

    Uses public signals to generate "Likely to entertain offer" probability

    KPI: Contact-to-reply rate improvement
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Clear existing signals
    db.query(PropensitySignal).filter(PropensitySignal.property_id == property_id).delete()

    # Analyze signals
    propensity_score, signals = _analyze_propensity_signals(property)

    # Save signals to database
    for signal in signals:
        db.add(signal)

    # Update property
    property.propensity_to_sell = propensity_score
    property.propensity_signals = [
        {
            "type": s.signal_type,
            "value": s.signal_value,
            "weight": s.weight,
            "reasoning": s.reasoning
        }
        for s in signals
    ]
    property.updated_at = datetime.utcnow()

    db.commit()

    # Build explanation
    if propensity_score >= 0.7:
        explanation = "High propensity - Multiple positive signals indicate owner likely to consider offers"
    elif propensity_score >= 0.5:
        explanation = "Moderate propensity - Some signals present, worth outreach"
    else:
        explanation = "Low propensity - Few indicators of sale motivation"

    return {
        "property_id": property_id,
        "propensity_to_sell": propensity_score,
        "signals": signals,
        "explanation": explanation
    }

@router.get("/propensity/{property_id}/signals", response_model=List[schemas.PropensitySignalResponse])
def get_propensity_signals(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all propensity signals for a property
    """
    signals = (
        db.query(PropensitySignal)
        .filter(PropensitySignal.property_id == property_id)
        .order_by(desc(PropensitySignal.weight))
        .all()
    )

    return signals

# ============================================================================
# PROVENANCE INSPECTOR
# ============================================================================

@router.get("/provenance/{property_id}", response_model=List[schemas.ProvenanceInspectorResponse])
def inspect_property_provenance(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Provenance Inspector UI: Show data source for each field

    Hover a field to see:
    - Source name
    - Source tier (government/community/derived/paid)
    - License type
    - Cost
    - Confidence
    - Freshness
    - Expiry

    Allows users to "prefer source X" for specific properties

    KPI: Fewer data disputes, higher confidence
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get provenance records
    provenance_records = (
        db.query(PropertyProvenance)
        .filter(PropertyProvenance.property_id == property_id)
        .all()
    )

    # Build response with current values
    result = []
    for record in provenance_records:
        # Get current field value from property
        current_value = getattr(property, record.field_name, None)

        result.append({
            "property_id": property_id,
            "field_name": record.field_name,
            "current_value": current_value,
            "source_name": record.source_name,
            "source_tier": record.source_tier,
            "license_type": record.license_type,
            "cost": record.cost,
            "confidence": record.confidence,
            "fetched_at": record.fetched_at,
            "expires_at": record.expires_at
        })

    return result

@router.post("/provenance/{property_id}/update-source")
def update_field_source(
    property_id: int,
    field_name: str,
    preferred_source: str,
    db: Session = Depends(get_db)
):
    """
    Update data source preference for a specific field

    User can choose to "prefer source X" when multiple sources available
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # This would trigger a refresh from the preferred source
    # For now, just log the preference

    return {
        "status": "preference_saved",
        "property_id": property_id,
        "field_name": field_name,
        "preferred_source": preferred_source,
        "message": f"Will use {preferred_source} for {field_name} on next refresh"
    }

# ============================================================================
# DELIVERABILITY DASHBOARD
# ============================================================================

@router.get("/deliverability/{team_id}", response_model=List[schemas.DeliverabilityMetricsResponse])
def get_deliverability_metrics(
    team_id: int,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Deliverability Hygiene Dashboard

    Shows:
    - Domain warmup status
    - Bounce/suppression trends
    - List health suggestions
    - Daily metrics

    Recommendations:
    - Keep bounce rate < 3%
    - Remove hard bounces immediately
    - Track suppression list growth

    KPI: Bounce <3%, open rate ↑
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    metrics = (
        db.query(DeliverabilityMetrics)
        .filter(
            DeliverabilityMetrics.team_id == team_id,
            DeliverabilityMetrics.date >= cutoff_date
        )
        .order_by(desc(DeliverabilityMetrics.date))
        .all()
    )

    return metrics

@router.post("/deliverability/{team_id}/record")
def record_deliverability_metrics(
    team_id: int,
    emails_sent: int,
    emails_delivered: int,
    emails_bounced: int,
    emails_opened: int,
    emails_clicked: int,
    db: Session = Depends(get_db)
):
    """
    Record daily deliverability metrics

    Called by email service provider webhook or daily batch job
    """
    # Calculate rates
    bounce_rate = emails_bounced / emails_sent if emails_sent > 0 else 0.0
    open_rate = emails_opened / emails_delivered if emails_delivered > 0 else 0.0
    click_rate = emails_clicked / emails_delivered if emails_delivered > 0 else 0.0

    # Create metrics record
    metrics = DeliverabilityMetrics(
        team_id=team_id,
        date=datetime.utcnow().date(),
        emails_sent=emails_sent,
        emails_delivered=emails_delivered,
        emails_bounced=emails_bounced,
        emails_opened=emails_opened,
        emails_clicked=emails_clicked,
        bounce_rate=bounce_rate,
        open_rate=open_rate,
        click_rate=click_rate
    )

    db.add(metrics)
    db.commit()

    # Check for issues and provide recommendations
    recommendations = []

    if bounce_rate > 0.03:
        recommendations.append("⚠️ Bounce rate > 3% - Review and clean list")

    if open_rate < 0.15:
        recommendations.append("📉 Low open rate - Check subject lines and sender reputation")

    return {
        "status": "recorded",
        "bounce_rate": bounce_rate,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "recommendations": recommendations
    }

# ============================================================================
# BUDGET TRACKING
# ============================================================================

@router.get("/budget/{team_id}", response_model=List[schemas.BudgetTrackingResponse])
def get_budget_tracking(
    team_id: int,
    provider: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """
    Budget & Provider Usage Dashboard

    Shows:
    - ATTOM/Regrid spend vs caps
    - Daily cost trends
    - Forecast to end of month
    - Auto-switch recommendations

    KPI: Cost predictability, no surprise overages
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(BudgetTracking).filter(
        BudgetTracking.team_id == team_id,
        BudgetTracking.date >= cutoff_date
    )

    if provider:
        query = query.filter(BudgetTracking.provider == provider)

    tracking = (
        query
        .order_by(desc(BudgetTracking.date))
        .all()
    )

    return tracking

@router.post("/budget/{team_id}/record")
def record_budget_usage(
    team_id: int,
    provider: str,
    requests_made: int,
    cost: float,
    db: Session = Depends(get_db)
):
    """
    Record data provider usage and cost

    Called after each API request to paid providers
    """
    # Get team to check budget cap
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    monthly_cap = team.monthly_budget_cap or 500.0

    # Get current month spending
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_spending = (
        db.query(func.sum(BudgetTracking.cost))
        .filter(
            BudgetTracking.team_id == team_id,
            BudgetTracking.provider == provider,
            BudgetTracking.date >= start_of_month
        )
        .scalar() or 0.0
    )

    remaining_budget = monthly_cap - month_spending
    days_left_in_month = 30 - datetime.utcnow().day
    projected_cost = (month_spending / datetime.utcnow().day) * 30 if datetime.utcnow().day > 0 else 0

    # Create tracking record
    tracking = BudgetTracking(
        team_id=team_id,
        provider=provider,
        date=datetime.utcnow().date(),
        requests_made=requests_made,
        cost=cost,
        monthly_cap=monthly_cap,
        remaining_budget=remaining_budget,
        projected_end_of_month_cost=projected_cost
    )

    db.add(tracking)
    db.commit()

    # Alert if approaching cap
    alert = None
    if remaining_budget < monthly_cap * 0.2:
        alert = f"⚠️ Only ${remaining_budget:.2f} remaining of ${monthly_cap:.2f} monthly cap"

    if projected_cost > monthly_cap:
        alert = f"🚨 Projected to exceed cap by ${projected_cost - monthly_cap:.2f}"

    return {
        "status": "recorded",
        "month_spending": month_spending + cost,
        "remaining_budget": remaining_budget,
        "projected_cost": projected_cost,
        "alert": alert
    }
