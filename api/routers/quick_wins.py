"""Quick wins router for one-click memo generation and sending."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import re

router = APIRouter(prefix="/quick-wins", tags=["quick-wins"])


# ============================================================================
# Schemas
# ============================================================================

class GenerateAndSendRequest(BaseModel):
    """Request to generate and send a memo."""
    property_id: int = Field(..., description="ID of the property")
    template_id: int = Field(..., description="ID of the template to use")


class GenerateAndSendResponse(BaseModel):
    """Response from generate and send operation."""
    property_id: int
    template_id: int
    memo_content: str
    sent_at: str
    recipient_email: str
    recipient_name: Optional[str] = None
    status: str = "sent"
    subject: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def substitute_variables(template_str: str, variables: Dict[str, Any]) -> str:
    """
    Replace {{variable}} placeholders in template with actual values.

    Args:
        template_str: Template string with {{variable}} placeholders
        variables: Dictionary of variable names to values

    Returns:
        String with all variables substituted
    """
    result = template_str

    # Find all {{variable}} patterns
    pattern = r'\{\{(\w+)\}\}'

    def replace_match(match):
        var_name = match.group(1)
        # Return the value if it exists, otherwise keep the placeholder
        return str(variables.get(var_name, match.group(0)))

    result = re.sub(pattern, replace_match, result)
    return result


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate-and-send", response_model=GenerateAndSendResponse)
def generate_and_send(request: GenerateAndSendRequest):
    """
    Generate a personalized memo from a template and send it to the property owner.

    In MOCK_MODE, this:
    1. Fetches the property data
    2. Fetches the template
    3. Performs variable substitution to create personalized content
    4. Returns a "sent" response without actually sending via email provider

    This endpoint demonstrates the memo generation workflow that would be used
    for automated, personalized outreach to property owners.
    """
    # Import here to avoid circular dependencies
    from api.routers.properties import MOCK_PROPERTIES
    from api.routers.templates import TEMPLATES

    # Find the property
    property_data = None
    for prop in MOCK_PROPERTIES:
        if prop.get("id") == str(request.property_id) or str(prop.get("id")) == str(request.property_id):
            property_data = prop
            break

    if not property_data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Property not found",
                "property_id": request.property_id
            }
        )

    # Find the template
    template_id = f"tpl_{str(request.template_id).zfill(3)}" if isinstance(request.template_id, int) else str(request.template_id)
    template_data = TEMPLATES.get(template_id)

    if not template_data:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Template not found",
                "template_id": request.template_id,
                "available_templates": list(TEMPLATES.keys())
            }
        )

    # Prepare variables for substitution
    variables = {
        # Property-related
        "property_address": property_data.get("address", ""),
        "city": property_data.get("city", ""),
        "state": property_data.get("state", ""),
        "zip": property_data.get("zip") or property_data.get("zip_code", ""),
        "price": f"${property_data.get('price', 0):,.0f}",
        "bedrooms": str(property_data.get("bedrooms", "")),
        "bathrooms": str(property_data.get("bathrooms", "")),
        "square_feet": f"{property_data.get('square_feet', 0):,}",

        # Owner-related
        "owner_name": property_data.get("owner_name", "Property Owner"),

        # Sender-related (mock data for demo)
        "sender_name": "Demo User",
        "sender_email": "demo@realestateos.com",
        "sender_phone": "(555) 123-4567",

        # Offer-related (mock data)
        "offer_amount": f"${int(property_data.get('price', 0) * 0.85):,.0f}",  # 85% of asking
        "closing_days": "30",
        "day_of_week": "Thursday",
        "alternative_day": "Friday",
    }

    # Generate memo by substituting variables in template
    subject = None
    if template_data.get("subject"):
        subject = substitute_variables(template_data["subject"], variables)

    memo_content = substitute_variables(template_data["body"], variables)

    # Determine recipient email (in real system, would come from property data)
    # For demo, generate a plausible email from owner name
    owner_name = property_data.get("owner_name", "Property Owner")
    if owner_name and owner_name != "Property Owner":
        # Simple email generation: first.last@example.com
        name_parts = owner_name.lower().split()
        if len(name_parts) >= 2:
            recipient_email = f"{name_parts[0]}.{name_parts[-1]}@example.com"
        else:
            recipient_email = f"{name_parts[0]}@example.com"
    else:
        # Fallback to property-based email
        address_parts = property_data.get("address", "").lower().split()
        if address_parts:
            recipient_email = f"owner.{address_parts[0]}@example.com"
        else:
            recipient_email = "owner@example.com"

    # In MOCK_MODE, we don't actually send the email
    # Just return success response
    return GenerateAndSendResponse(
        property_id=request.property_id,
        template_id=request.template_id,
        memo_content=memo_content,
        sent_at=datetime.now().isoformat(),
        recipient_email=recipient_email,
        recipient_name=owner_name if owner_name != "Property Owner" else None,
        status="sent",
        subject=subject
    )


@router.post("/flag-data-issue")
def flag_data_issue(property_id: int, issue_type: str):
    """
    Flag a data quality issue for a property.

    This is a placeholder endpoint that would allow users to report
    missing or incorrect data (e.g., missing owner name, wrong phone number).

    In a real system, this would create a task for the data team to investigate.
    """
    return {
        "property_id": property_id,
        "issue_type": issue_type,
        "status": "flagged",
        "flagged_at": datetime.now().isoformat(),
        "message": f"Data issue '{issue_type}' flagged for property {property_id}. Data team will investigate."
    }
