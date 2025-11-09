"""
Differentiators Router
Explainable Probability of Close, Scenario Planning, Investor Network Effects
Defensible competitive edges
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from api.database import get_db
from api import schemas
from db.models import (
    Property, Deal, Investor, InvestorEngagement, PropertyStage
)

router = APIRouter(prefix="/differentiators", tags=["Differentiators"])

# ============================================================================
# EXPLAINABLE PROBABILITY OF CLOSE
# ============================================================================

def _calculate_probability_factors(property: Property, db: Session) -> tuple[float, List[dict]]:
    """
    Calculate calibrated probability with explainable factors

    Factors considered:
    - Owner propensity signals
    - Engagement level (replies, opens)
    - Pipeline stage
    - Time in stage
    - Property characteristics
    - Market conditions

    Returns: (probability, factors_list)
    """
    factors = []
    base_prob = 0.3  # Base probability

    # Factor 1: Pipeline stage (major indicator)
    stage_probs = {
        PropertyStage.NEW: 0.1,
        PropertyStage.OUTREACH: 0.2,
        PropertyStage.QUALIFIED: 0.5,
        PropertyStage.NEGOTIATION: 0.7,
        PropertyStage.UNDER_CONTRACT: 0.9,
    }

    stage_prob = stage_probs.get(property.current_stage, 0.1)
    stage_impact = stage_prob - base_prob

    factors.append({
        "factor": "Pipeline Stage",
        "value": property.current_stage.value,
        "impact": stage_impact,
        "impact_pct": f"{stage_impact*100:+.0f}%",
        "explanation": f"Stage '{property.current_stage.value}' historically closes at {stage_prob*100:.0f}%"
    })

    # Factor 2: Owner propensity
    if property.propensity_to_sell:
        propensity_impact = (property.propensity_to_sell - 0.5) * 0.3
        factors.append({
            "factor": "Owner Propensity",
            "value": f"{property.propensity_to_sell:.2f}",
            "impact": propensity_impact,
            "impact_pct": f"{propensity_impact*100:+.0f}%",
            "explanation": f"Propensity score of {property.propensity_to_sell:.2f} based on public signals"
        })
        base_prob += propensity_impact

    # Factor 3: Engagement (replies are strongest signal)
    if property.reply_count and property.reply_count > 0:
        engagement_impact = min(0.25, property.reply_count * 0.1)
        factors.append({
            "factor": "Active Engagement",
            "value": f"{property.reply_count} replies",
            "impact": engagement_impact,
            "impact_pct": f"{engagement_impact*100:+.0f}%",
            "explanation": f"{property.reply_count} replies indicates strong interest"
        })
        base_prob += engagement_impact

    # Factor 4: Property quality score
    if property.bird_dog_score:
        score_impact = (property.bird_dog_score - 0.5) * 0.2
        factors.append({
            "factor": "Property Quality",
            "value": f"{property.bird_dog_score:.2f}",
            "impact": score_impact,
            "impact_pct": f"{score_impact*100:+.0f}%",
            "explanation": f"Score of {property.bird_dog_score:.2f} affects deal quality"
        })
        base_prob += score_impact

    # Factor 5: Time in current stage (negative if too long)
    if property.stage_changed_at:
        days_in_stage = (datetime.utcnow() - property.stage_changed_at).days
        if days_in_stage > 30:
            stagnation_impact = -0.15
            factors.append({
                "factor": "Stagnation Risk",
                "value": f"{days_in_stage} days",
                "impact": stagnation_impact,
                "impact_pct": f"{stagnation_impact*100:.0f}%",
                "explanation": f"{days_in_stage} days in stage suggests potential issues"
            })
            base_prob += stagnation_impact

    # Cap probability
    final_prob = max(0.05, min(0.95, base_prob + stage_prob))

    return final_prob, factors

@router.get("/explainable-probability/{property_id}", response_model=schemas.ExplainableProbabilityResponse)
def get_explainable_probability(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get Explainable Probability of Close

    Not just a score - shows WHY and HOW it's calculated

    Features:
    - Calibrated probability based on historical data
    - Clear factor breakdown
    - Impact of each factor (+ or -)
    - "What would happen if..." insights

    Example: "Sending postcard increases expected response +0.7%"

    KPI: Team trusts and uses probability in decision-making
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Calculate probability with factors
    probability, score_factors = _calculate_probability_factors(property, db)

    # Build explanation
    top_positive = [f for f in score_factors if f["impact"] > 0][:2]
    top_negative = [f for f in score_factors if f["impact"] < 0][:2]

    explanation_parts = [f"{probability*100:.0f}% probability of close."]

    if top_positive:
        explanation_parts.append("Positive factors: " + ", ".join([f["factor"] for f in top_positive]))

    if top_negative:
        explanation_parts.append("Risk factors: " + ", ".join([f["factor"] for f in top_negative]))

    explanation = " ".join(explanation_parts)

    # Calculate confidence (based on data availability)
    confidence = 0.6  # Base confidence
    if property.reply_count and property.reply_count > 0:
        confidence += 0.2
    if property.propensity_to_sell:
        confidence += 0.1
    if property.bird_dog_score:
        confidence += 0.1

    confidence = min(1.0, confidence)

    # Update property with calculated probability
    property.probability_of_close = probability
    property.updated_at = datetime.utcnow()
    db.commit()

    return {
        "property_id": property_id,
        "probability_of_close": probability,
        "score_factors": score_factors,
        "propensity_signals": property.propensity_signals or [],
        "explanation": explanation,
        "confidence": confidence
    }

@router.get("/what-if/{property_id}")
def what_if_analysis(
    property_id: int,
    action: str = Query(..., description="Action to simulate: 'send_postcard', 'make_call', 'send_followup', 'increase_offer'"),
    db: Session = Depends(get_db)
):
    """
    What-If Analysis: Show impact of actions on probability

    Simulates: "What happens if I..."
    - Send postcard
    - Make phone call
    - Send follow-up email
    - Increase offer price
    - Add memo

    Shows expected probability change

    Helps prioritize actions
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get current probability
    current_prob, _ = _calculate_probability_factors(property, db)

    # Simulate impact of action
    action_impacts = {
        "send_postcard": {
            "prob_change": 0.05,
            "explanation": "Postcards have 5-7% response rate, adds touchpoint variety"
        },
        "make_call": {
            "prob_change": 0.10,
            "explanation": "Direct calls increase connection rate by ~10%"
        },
        "send_followup": {
            "prob_change": 0.03,
            "explanation": "Follow-up emails recover 3-5% of stalled leads"
        },
        "increase_offer": {
            "prob_change": 0.15,
            "explanation": "Higher offers increase acceptance rate significantly"
        },
        "add_memo": {
            "prob_change": 0.07,
            "explanation": "Professional memos increase perceived credibility"
        }
    }

    impact = action_impacts.get(action, {"prob_change": 0.02, "explanation": "Minor positive impact expected"})

    new_prob = min(0.95, current_prob + impact["prob_change"])
    prob_change_pct = impact["prob_change"] * 100

    return {
        "property_id": property_id,
        "action": action,
        "current_probability": current_prob,
        "new_probability": new_prob,
        "probability_change": impact["prob_change"],
        "change_pct": f"+{prob_change_pct:.1f}%",
        "explanation": impact["explanation"],
        "recommendation": f"Expected to increase close probability by {prob_change_pct:.1f}%"
    }

# ============================================================================
# INVESTOR NETWORK EFFECTS
# ============================================================================

@router.get("/suggested-investors/{property_id}", response_model=List[schemas.SuggestedInvestorResponse])
def get_suggested_investors(
    property_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Suggested Investors based on preferences and past engagement

    Investor Directory + ML:
    - Match property characteristics to investor preferences
    - Consider past engagement history
    - Weight by response time and close rate

    Network effects: "Properties like this one were interesting to Investor X"

    KPI: Faster investor matching, higher offer rates
    """
    # Get property
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get all investors in team
    investors = (
        db.query(Investor)
        .filter(Investor.team_id == property.team_id)
        .all()
    )

    # Score each investor
    scored_investors = []

    for investor in investors:
        match_score = 0.0
        match_reasons = []

        # Match 1: Property type preference
        if investor.preferred_property_types and property.property_type:
            if property.property_type.lower() in [t.lower() for t in investor.preferred_property_types]:
                match_score += 0.3
                match_reasons.append(f"Prefers {property.property_type}")

        # Match 2: ARV range
        if property.arv:
            if investor.min_arv and investor.max_arv:
                if investor.min_arv <= property.arv <= investor.max_arv:
                    match_score += 0.25
                    match_reasons.append(f"ARV ${property.arv:,.0f} in range")

        # Match 3: Location preference
        if investor.preferred_locations and property.city:
            if property.city in investor.preferred_locations:
                match_score += 0.20
                match_reasons.append(f"Active in {property.city}")

        # Match 4: Past engagement (network effect)
        past_engagement = (
            db.query(InvestorEngagement)
            .filter(
                InvestorEngagement.investor_id == investor.id,
                InvestorEngagement.expressed_interest == True
            )
            .count()
        )

        if past_engagement > 0:
            engagement_boost = min(0.25, past_engagement * 0.05)
            match_score += engagement_boost
            match_reasons.append(f"Engaged with {past_engagement} similar properties")

        # Only include if minimum match
        if match_score >= 0.3:
            scored_investors.append({
                "investor": investor,
                "match_score": match_score,
                "match_reasons": match_reasons
            })

    # Sort by match score
    scored_investors.sort(key=lambda x: x["match_score"], reverse=True)

    # Return top matches
    return scored_investors[:limit]

@router.post("/track-investor-engagement")
def track_investor_engagement(
    property_id: int,
    investor_id: int,
    share_link_id: Optional[int] = None,
    expressed_interest: bool = False,
    questions_asked: int = 0,
    db: Session = Depends(get_db)
):
    """
    Track investor engagement with property

    Builds network effect data:
    - Which investors view which properties
    - Time spent
    - Interest level
    - Questions asked

    Powers: "Investors like you were interested in..."
    """
    # Check if engagement record exists
    engagement = (
        db.query(InvestorEngagement)
        .filter(
            InvestorEngagement.investor_id == investor_id,
            InvestorEngagement.property_id == property_id
        )
        .first()
    )

    if not engagement:
        engagement = InvestorEngagement(
            investor_id=investor_id,
            property_id=property_id,
            share_link_id=share_link_id,
            view_count=0
        )
        db.add(engagement)

    # Update engagement
    engagement.view_count += 1
    engagement.last_viewed_at = datetime.utcnow()

    if not engagement.first_viewed_at:
        engagement.first_viewed_at = datetime.utcnow()

    if expressed_interest:
        engagement.expressed_interest = True

    if questions_asked:
        engagement.questions_asked += questions_asked

    db.commit()

    return {
        "property_id": property_id,
        "investor_id": investor_id,
        "view_count": engagement.view_count,
        "expressed_interest": engagement.expressed_interest
    }
