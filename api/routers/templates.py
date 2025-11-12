"""Templates router for email and communication templates."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/templates", tags=["templates"])


# ============================================================================
# Enums
# ============================================================================

class TemplateType(str, Enum):
    """Type of communication template."""
    email = "email"
    sms = "sms"
    letter = "letter"
    voicemail = "voicemail"


class TemplateCategory(str, Enum):
    """Category of template for organization."""
    initial_outreach = "initial_outreach"
    follow_up = "follow_up"
    negotiation = "negotiation"
    closing = "closing"
    maintenance = "maintenance"
    other = "other"


# ============================================================================
# Schemas
# ============================================================================

class TemplateCreate(BaseModel):
    """Request to create a template."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    template_type: TemplateType
    category: TemplateCategory
    subject: Optional[str] = Field(None, description="Email subject line (email templates only)")
    body: str = Field(..., min_length=1, description="Template content with {{variables}}")
    tags: Optional[List[str]] = []


class TemplateUpdate(BaseModel):
    """Request to update a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    template_type: Optional[TemplateType] = None
    category: Optional[TemplateCategory] = None
    subject: Optional[str] = None
    body: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None


class Template(BaseModel):
    """Template response."""
    id: str
    name: str
    description: Optional[str]
    template_type: TemplateType
    category: TemplateCategory
    subject: Optional[str]
    body: str
    tags: List[str]
    variables: List[str] = Field(description="List of {{variables}} found in template")
    usage_count: int = Field(description="Number of times template has been used")
    created_at: str
    updated_at: str
    created_by: str


class TemplatePreviewRequest(BaseModel):
    """Request to preview a template with variable substitution."""
    variables: Dict[str, Any] = Field(
        ...,
        description="Variable values to substitute into template",
        example={
            "owner_name": "John Smith",
            "property_address": "1234 Main St",
            "offer_amount": "$500,000"
        }
    )


class TemplatePreview(BaseModel):
    """Preview of template with variables substituted."""
    template_id: str
    subject: Optional[str] = Field(None, description="Subject with variables substituted")
    body: str = Field(description="Body with variables substituted")
    missing_variables: List[str] = Field(
        description="Variables in template that were not provided"
    )


# ============================================================================
# Helper Functions
# ============================================================================

def extract_variables(text: str) -> List[str]:
    """
    Extract {{variable}} placeholders from text.

    Args:
        text: Text containing {{variable}} placeholders

    Returns:
        List of variable names without braces
    """
    import re
    pattern = r'\{\{(\w+)\}\}'
    return list(set(re.findall(pattern, text)))


def substitute_variables(text: str, variables: Dict[str, Any]) -> tuple[str, List[str]]:
    """
    Substitute variables in text.

    Args:
        text: Text with {{variable}} placeholders
        variables: Dict of variable names to values

    Returns:
        Tuple of (substituted_text, missing_variables)
    """
    import re

    # Find all variables in text
    all_vars = extract_variables(text)
    missing = [var for var in all_vars if var not in variables]

    # Substitute provided variables
    result = text
    for var_name, var_value in variables.items():
        pattern = r'\{\{' + var_name + r'\}\}'
        result = re.sub(pattern, str(var_value), result)

    return result, missing


# ============================================================================
# Mock Data Store
# ============================================================================

TEMPLATES: Dict[str, Dict] = {
    "tpl_001": {
        "id": "tpl_001",
        "name": "Initial Outreach - Off Market Interest",
        "description": "First contact email for off-market property owners",
        "template_type": "email",
        "category": "initial_outreach",
        "subject": "Interest in your property at {{property_address}}",
        "body": """Hi {{owner_name}},

My name is {{sender_name}} and I'm a real estate investor specializing in {{city}} properties.

I noticed your property at {{property_address}} and wanted to reach out to see if you'd be open to discussing a potential purchase. I'm not a real estate agent - I buy properties directly and can close quickly with cash if the numbers make sense.

Would you be open to a brief conversation about your property?

Best regards,
{{sender_name}}
{{sender_phone}}
{{sender_email}}""",
        "tags": ["off-market", "initial-contact", "cash-offer"],
        "usage_count": 142,
        "created_at": "2025-10-01T10:00:00",
        "updated_at": "2025-11-05T14:30:00",
        "created_by": "demo@realestateos.com"
    },
    "tpl_002": {
        "id": "tpl_002",
        "name": "Follow-Up - Second Contact",
        "description": "Follow-up email after initial outreach with no response",
        "template_type": "email",
        "category": "follow_up",
        "subject": "Following up: {{property_address}}",
        "body": """Hi {{owner_name}},

I reached out last week about your property at {{property_address}}. I understand you may be busy, so I wanted to follow up briefly.

I'm still very interested in the property and would love to discuss a potential offer. I can work around your schedule for a quick call.

Would {{day_of_week}} or {{alternative_day}} work for a 10-minute conversation?

Thanks,
{{sender_name}}
{{sender_phone}}""",
        "tags": ["follow-up", "second-contact"],
        "usage_count": 87,
        "created_at": "2025-10-05T11:00:00",
        "updated_at": "2025-10-20T09:15:00",
        "created_by": "demo@realestateos.com"
    },
    "tpl_003": {
        "id": "tpl_003",
        "name": "Offer Presentation",
        "description": "Email presenting a formal offer to property owner",
        "template_type": "email",
        "category": "negotiation",
        "subject": "Offer for {{property_address}}",
        "body": """Hi {{owner_name}},

Thank you for taking the time to discuss your property at {{property_address}}.

Based on our conversation and my analysis of the property and comparable sales in the area, I'd like to present an offer of {{offer_amount}}.

This offer includes:
- All-cash purchase (no financing contingency)
- {{closing_days}}-day closing period
- We cover all closing costs
- Property sold as-is (no repairs needed)

I've attached a formal offer letter with all details. Please review and let me know if you have any questions or would like to discuss further.

Looking forward to working with you,
{{sender_name}}
{{sender_phone}}
{{sender_email}}""",
        "tags": ["offer", "negotiation", "cash"],
        "usage_count": 34,
        "created_at": "2025-10-10T15:00:00",
        "updated_at": "2025-11-01T10:00:00",
        "created_by": "demo@realestateos.com"
    },
    "tpl_004": {
        "id": "tpl_004",
        "name": "SMS - Quick Check-In",
        "description": "SMS template for quick follow-ups",
        "template_type": "sms",
        "category": "follow_up",
        "subject": None,
        "body": """Hi {{owner_name}}, this is {{sender_name}}. Still interested in your property at {{property_address}}. Are you open to a quick call this week? Thanks!""",
        "tags": ["sms", "quick-follow-up"],
        "usage_count": 203,
        "created_at": "2025-09-15T09:00:00",
        "updated_at": "2025-10-30T16:00:00",
        "created_by": "demo@realestateos.com"
    },
    "tpl_005": {
        "id": "tpl_005",
        "name": "Post-Closing Thank You",
        "description": "Thank you email after successful property closing",
        "template_type": "email",
        "category": "closing",
        "subject": "Thank you - {{property_address}} closing",
        "body": """Hi {{owner_name}},

I wanted to reach out and thank you for working with us on the sale of {{property_address}}. It was a pleasure doing business with you.

The closing went smoothly, and I hope the process was as stress-free as possible for you. If you have any questions about anything or need any documentation, please don't hesitate to reach out.

Also, if you know anyone else looking to sell their property, I'd appreciate any referrals. I always treat people fairly and aim to make the process as smooth as possible.

Wishing you all the best,
{{sender_name}}
{{sender_phone}}
{{sender_email}}""",
        "tags": ["closing", "thank-you", "referral"],
        "usage_count": 12,
        "created_at": "2025-10-25T12:00:00",
        "updated_at": "2025-11-08T11:00:00",
        "created_by": "demo@realestateos.com"
    }
}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[Template])
def list_templates(
    template_type: Optional[TemplateType] = None,
    category: Optional[TemplateCategory] = None,
    search: Optional[str] = None
):
    """
    List all templates with optional filters.

    Filter by type, category, or search term in name/description.
    """
    templates = list(TEMPLATES.values())

    # Apply filters
    if template_type:
        templates = [t for t in templates if t["template_type"] == template_type.value]
    if category:
        templates = [t for t in templates if t["category"] == category.value]
    if search:
        search_lower = search.lower()
        templates = [
            t for t in templates
            if search_lower in t["name"].lower()
            or (t["description"] and search_lower in t["description"].lower())
        ]

    # Add variables to each template
    result = []
    for t in templates:
        template_dict = t.copy()
        # Extract variables from subject and body
        variables = extract_variables(t.get("subject", "") or "")
        variables.extend(extract_variables(t["body"]))
        template_dict["variables"] = list(set(variables))
        result.append(Template(**template_dict))

    return result


@router.post("/", response_model=Template, status_code=201)
def create_template(template: TemplateCreate):
    """
    Create a new template.

    Templates can include {{variables}} for dynamic content substitution.
    Variables will be automatically extracted and listed.
    """
    # Generate new ID
    new_id = f"tpl_{str(len(TEMPLATES) + 1).zfill(3)}"

    new_template = {
        "id": new_id,
        "name": template.name,
        "description": template.description,
        "template_type": template.template_type.value,
        "category": template.category.value,
        "subject": template.subject,
        "body": template.body,
        "tags": template.tags or [],
        "usage_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    TEMPLATES[new_id] = new_template

    # Extract variables for response
    variables = extract_variables(template.subject or "")
    variables.extend(extract_variables(template.body))
    new_template["variables"] = list(set(variables))

    return Template(**new_template)


@router.get("/{template_id}", response_model=Template)
def get_template(template_id: str):
    """
    Get a specific template by ID.

    Returns the template with all {{variables}} extracted.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[template_id].copy()

    # Extract variables
    variables = extract_variables(template.get("subject", "") or "")
    variables.extend(extract_variables(template["body"]))
    template["variables"] = list(set(variables))

    return Template(**template)


@router.put("/{template_id}", response_model=Template)
def update_template(template_id: str, update: TemplateUpdate):
    """
    Update an existing template.

    All fields are optional. Variables will be re-extracted if body/subject changes.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[template_id]

    # Update fields
    if update.name is not None:
        template["name"] = update.name
    if update.description is not None:
        template["description"] = update.description
    if update.template_type is not None:
        template["template_type"] = update.template_type.value
    if update.category is not None:
        template["category"] = update.category.value
    if update.subject is not None:
        template["subject"] = update.subject
    if update.body is not None:
        template["body"] = update.body
    if update.tags is not None:
        template["tags"] = update.tags

    template["updated_at"] = datetime.now().isoformat()

    # Extract variables for response
    variables = extract_variables(template.get("subject", "") or "")
    variables.extend(extract_variables(template["body"]))
    template["variables"] = list(set(variables))

    return Template(**template)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: str):
    """
    Delete a template.

    Removes the template from the system.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    del TEMPLATES[template_id]
    return None


@router.post("/{template_id}/preview", response_model=TemplatePreview)
def preview_template(template_id: str, preview_request: TemplatePreviewRequest):
    """
    Preview a template with variable substitution.

    Substitutes provided variables into the template and returns the result.
    Also reports any missing variables that were not provided.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[template_id]
    variables = preview_request.variables

    # Substitute variables in subject (if exists)
    preview_subject = None
    missing_subject_vars = []
    if template.get("subject"):
        preview_subject, missing_subject_vars = substitute_variables(
            template["subject"],
            variables
        )

    # Substitute variables in body
    preview_body, missing_body_vars = substitute_variables(
        template["body"],
        variables
    )

    # Combine missing variables
    all_missing = list(set(missing_subject_vars + missing_body_vars))

    return TemplatePreview(
        template_id=template_id,
        subject=preview_subject,
        body=preview_body,
        missing_variables=all_missing
    )


@router.post("/{template_id}/duplicate", response_model=Template, status_code=201)
def duplicate_template(template_id: str, new_name: Optional[str] = None):
    """
    Duplicate an existing template.

    Creates a copy of the template with a new ID and optional new name.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    original = TEMPLATES[template_id]

    # Generate new ID
    new_id = f"tpl_{str(len(TEMPLATES) + 1).zfill(3)}"

    # Create duplicate
    duplicate = {
        "id": new_id,
        "name": new_name or f"{original['name']} (Copy)",
        "description": original["description"],
        "template_type": original["template_type"],
        "category": original["category"],
        "subject": original.get("subject"),
        "body": original["body"],
        "tags": original["tags"].copy(),
        "usage_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    TEMPLATES[new_id] = duplicate

    # Extract variables for response
    variables = extract_variables(duplicate.get("subject", "") or "")
    variables.extend(extract_variables(duplicate["body"]))
    duplicate["variables"] = list(set(variables))

    return Template(**duplicate)


@router.get("/{template_id}/usage-stats")
def get_template_usage_stats(template_id: str):
    """
    Get usage statistics for a template.

    Returns how many times the template has been used,
    recent usage, and performance metrics.
    """
    if template_id not in TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[template_id]

    # Mock usage stats
    import random

    return {
        "template_id": template_id,
        "total_uses": template["usage_count"],
        "uses_last_30_days": random.randint(5, template["usage_count"]),
        "uses_last_7_days": random.randint(1, 10),
        "average_response_rate": round(random.uniform(0.15, 0.45), 2),
        "average_conversion_rate": round(random.uniform(0.05, 0.15), 2),
        "most_common_variables": [
            {"name": "owner_name", "usage_count": template["usage_count"]},
            {"name": "property_address", "usage_count": template["usage_count"]},
            {"name": "sender_name", "usage_count": template["usage_count"] - 2}
        ]
    }
