"""
Onboarding Router
Starter presets by persona, Guided tour, Outcome-based pricing setup
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api.database import get_db
from api import schemas
from db.models import (
    User, UserOnboarding, PresetTemplate, SmartList, Template
)

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# ============================================================================
# PRESET TEMPLATES
# ============================================================================

@router.get("/presets", response_model=List[schemas.PresetTemplateResponse])
def list_preset_templates(db: Session = Depends(get_db)):
    """
    List available starter presets by persona

    Presets:
    - Wholesaler Starter: High-volume outreach, quick turn
    - Small Fix-and-Flip: Renovation focus, contractor network
    - Institutional Single-Family: Scale operations, compliance focus
    """
    presets = db.query(PresetTemplate).all()

    # If no presets exist, create defaults
    if not presets:
        default_presets = [
            PresetTemplate(
                persona="wholesaler_starter",
                name="Wholesaler Starter",
                description="High-volume outreach focused on quick assignments",
                default_filters={
                    "bird_dog_score__gte": 0.6,
                    "has_reply": False,
                    "current_stage": "outreach"
                },
                default_templates=[
                    {"name": "Initial Outreach", "type": "email", "stage": "outreach"},
                    {"name": "Follow-Up #1", "type": "email", "stage": "outreach"},
                    {"name": "SMS Quick Hit", "type": "sms", "stage": "qualified"}
                ],
                dashboard_tiles=[
                    {"type": "pipeline_stats", "position": 1},
                    {"type": "next_best_actions", "position": 2},
                    {"type": "warm_replies", "position": 3}
                ]
            ),
            PresetTemplate(
                persona="fix_and_flip",
                name="Small Fix-and-Flip",
                description="Renovation-focused with ARV analysis",
                default_filters={
                    "repair_estimate__gte": 30000,
                    "arv__is_not_null": True
                },
                default_templates=[
                    {"name": "ARV Opportunity", "type": "email", "stage": "outreach"},
                    {"name": "Contractor Ready", "type": "email", "stage": "negotiation"}
                ],
                dashboard_tiles=[
                    {"type": "deal_economics", "position": 1},
                    {"type": "high_margin_deals", "position": 2},
                    {"type": "renovation_pipeline", "position": 3}
                ]
            ),
            PresetTemplate(
                persona="institutional",
                name="Institutional Single-Family",
                description="Scale operations with compliance and reporting",
                default_filters={
                    "arv__gte": 200000,
                    "compliance_clear": True
                },
                default_templates=[
                    {"name": "Portfolio Opportunity", "type": "email", "stage": "outreach"},
                    {"name": "Investor Packet", "type": "email", "stage": "negotiation"}
                ],
                dashboard_tiles=[
                    {"type": "portfolio_performance", "position": 1},
                    {"type": "compliance_dashboard", "position": 2},
                    {"type": "budget_tracking", "position": 3},
                    {"type": "deliverability", "position": 4}
                ]
            )
        ]

        for preset in default_presets:
            db.add(preset)

        db.commit()
        presets = db.query(PresetTemplate).all()

    return presets

@router.post("/apply-preset", response_model=schemas.UserOnboardingResponse)
def apply_preset(
    request: schemas.ApplyPresetRequest,
    db: Session = Depends(get_db)
):
    """
    Apply a preset template to user's account

    Sets up:
    - Default Smart Lists based on preset filters
    - Template library for persona
    - Dashboard layout
    - Initial onboarding steps
    """
    # Get user
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get preset
    preset = db.query(PresetTemplate).filter(PresetTemplate.persona == request.persona).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Get or create onboarding record
    onboarding = db.query(UserOnboarding).filter(UserOnboarding.user_id == request.user_id).first()

    if not onboarding:
        onboarding = UserOnboarding(
            user_id=request.user_id,
            steps_completed=[],
            persona_preset=request.persona
        )
        db.add(onboarding)
    else:
        onboarding.persona_preset = request.persona

    # Create default Smart Lists from preset
    for filter_config in [preset.default_filters]:
        smart_list = SmartList(
            team_id=user.team_id,
            created_by_user_id=user.id,
            name=f"{preset.name} - Main List",
            description="Auto-created from preset",
            filters=filter_config,
            is_dynamic=True
        )
        db.add(smart_list)

    # Mark preset applied step as complete
    if "preset_applied" not in onboarding.steps_completed:
        onboarding.steps_completed.append("preset_applied")

    db.commit()
    db.refresh(onboarding)

    return onboarding

# ============================================================================
# GUIDED TOUR / CHECKLIST
# ============================================================================

@router.get("/checklist/{user_id}", response_model=schemas.UserOnboardingResponse)
def get_onboarding_checklist(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get user's onboarding checklist

    5-step checklist:
    1. Choose preset persona
    2. Import first properties
    3. Create first template
    4. Send first outreach
    5. Complete first deal

    Shows progress and next steps
    """
    onboarding = db.query(UserOnboarding).filter(UserOnboarding.user_id == user_id).first()

    if not onboarding:
        # Create new onboarding
        onboarding = UserOnboarding(
            user_id=user_id,
            steps_completed=[]
        )
        db.add(onboarding)
        db.commit()
        db.refresh(onboarding)

    return onboarding

@router.post("/checklist/{user_id}/complete-step")
def complete_onboarding_step(
    user_id: int,
    step: str,
    db: Session = Depends(get_db)
):
    """
    Mark an onboarding step as complete

    Steps:
    - preset_selected
    - first_property_imported
    - first_template_created
    - first_outreach_sent
    - first_deal_created
    """
    onboarding = db.query(UserOnboarding).filter(UserOnboarding.user_id == user_id).first()

    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    if step not in onboarding.steps_completed:
        onboarding.steps_completed.append(step)

    # Check if all steps complete
    required_steps = [
        "preset_selected",
        "first_property_imported",
        "first_template_created",
        "first_outreach_sent",
        "first_deal_created"
    ]

    if all(s in onboarding.steps_completed for s in required_steps):
        onboarding.is_complete = True
        onboarding.completed_at = datetime.utcnow()

    db.commit()

    return {
        "user_id": user_id,
        "step_completed": step,
        "total_completed": len(onboarding.steps_completed),
        "is_complete": onboarding.is_complete
    }
