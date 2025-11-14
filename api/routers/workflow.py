"""Workflow router for smart lists and next-best-actions."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ============================================================================
# Enums
# ============================================================================

class SmartListOperator(str, Enum):
    """Operators for smart list filters."""
    equals = "equals"
    not_equals = "not_equals"
    contains = "contains"
    not_contains = "not_contains"
    greater_than = "greater_than"
    less_than = "less_than"
    between = "between"
    in_list = "in"
    not_in_list = "not_in"


class NBAStatus(str, Enum):
    """Status of a Next-Best-Action."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    dismissed = "dismissed"


class NBAPriority(str, Enum):
    """Priority level of a Next-Best-Action."""
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


# ============================================================================
# Schemas
# ============================================================================

class FilterCriteria(BaseModel):
    """Individual filter criterion for smart list."""
    field: str = Field(..., description="Property field to filter on")
    operator: SmartListOperator
    value: Any = Field(..., description="Value to compare against")


class SmartListCreate(BaseModel):
    """Request to create a smart list."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    filters: List[FilterCriteria] = Field(..., min_items=1)
    tags: Optional[List[str]] = []


class SmartListUpdate(BaseModel):
    """Request to update a smart list."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    filters: Optional[List[FilterCriteria]] = None
    tags: Optional[List[str]] = None


class SmartList(BaseModel):
    """Smart list response."""
    id: str
    name: str
    description: Optional[str]
    filters: List[FilterCriteria]
    tags: List[str]
    property_count: int
    created_at: str
    updated_at: str
    created_by: str


class PropertySummary(BaseModel):
    """Summary of a property for smart list results."""
    id: str
    address: str
    city: str
    state: str
    zip_code: str
    property_type: str
    status: str
    estimated_value: Optional[float]
    score: Optional[float]
    owner_name: Optional[str]
    last_contact: Optional[str]


class NextBestActionGenerate(BaseModel):
    """Request to generate NBA for a property."""
    property_id: str
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for NBA generation"
    )


class NextBestAction(BaseModel):
    """Next-Best-Action recommendation."""
    id: str
    property_id: str
    action_type: str  # e.g., "call", "email", "research", "visit"
    title: str
    description: str
    priority: NBAPriority
    status: NBAStatus
    reasoning: str  # AI explanation for why this action
    estimated_impact: str  # e.g., "high", "medium", "low"
    estimated_effort: str  # e.g., "5 minutes", "1 hour"
    due_date: Optional[str]
    completed_at: Optional[str]
    completed_by: Optional[str]
    created_at: str


class NBAComplete(BaseModel):
    """Request to mark NBA as complete."""
    notes: Optional[str] = Field(None, description="Completion notes")
    outcome: Optional[str] = Field(None, description="Outcome of the action")


# ============================================================================
# Mock Data Store
# ============================================================================

# In-memory store for smart lists
SMART_LISTS: Dict[str, Dict] = {
    "sl_001": {
        "id": "sl_001",
        "name": "High-Value Off-Market Properties",
        "description": "Properties over $500K that are off-market with recent distress signals",
        "filters": [
            {
                "field": "estimated_value",
                "operator": "greater_than",
                "value": 500000
            },
            {
                "field": "status",
                "operator": "equals",
                "value": "off_market"
            },
            {
                "field": "distress_score",
                "operator": "greater_than",
                "value": 0.7
            }
        ],
        "tags": ["high-value", "off-market", "distress"],
        "property_count": 47,
        "created_at": "2025-11-01T10:00:00",
        "updated_at": "2025-11-10T15:30:00",
        "created_by": "demo@realestateos.com"
    },
    "sl_002": {
        "id": "sl_002",
        "name": "Recent Owner Changes",
        "description": "Properties with ownership changes in the last 90 days",
        "filters": [
            {
                "field": "owner_change_date",
                "operator": "greater_than",
                "value": "2025-08-12"
            }
        ],
        "tags": ["owner-change", "recent"],
        "property_count": 23,
        "created_at": "2025-10-15T09:00:00",
        "updated_at": "2025-11-12T08:00:00",
        "created_by": "demo@realestateos.com"
    },
    "sl_003": {
        "id": "sl_003",
        "name": "Vacant Properties - Prime Locations",
        "description": "Vacant properties in high-growth zip codes",
        "filters": [
            {
                "field": "occupancy_status",
                "operator": "equals",
                "value": "vacant"
            },
            {
                "field": "zip_code",
                "operator": "in",
                "value": ["94102", "94103", "94107", "94110"]
            }
        ],
        "tags": ["vacant", "prime-location"],
        "property_count": 12,
        "created_at": "2025-09-20T14:00:00",
        "updated_at": "2025-11-11T11:00:00",
        "created_by": "demo@realestateos.com"
    }
}

# In-memory store for Next-Best-Actions
NEXT_BEST_ACTIONS: Dict[str, Dict] = {
    "nba_001": {
        "id": "nba_001",
        "property_id": "prop_001",
        "action_type": "email",
        "title": "Send initial outreach email",
        "description": "Reach out to owner about potential off-market purchase",
        "priority": "high",
        "status": "pending",
        "reasoning": "Property shows distress signals (tax delinquency, code violations). Owner may be motivated to sell.",
        "estimated_impact": "high",
        "estimated_effort": "10 minutes",
        "due_date": "2025-11-15T17:00:00",
        "completed_at": None,
        "completed_by": None,
        "created_at": "2025-11-12T09:00:00"
    },
    "nba_002": {
        "id": "nba_002",
        "property_id": "prop_002",
        "action_type": "research",
        "title": "Research recent comparable sales",
        "description": "Find 3-5 comparable sales within 0.5 miles to determine fair offer price",
        "priority": "medium",
        "status": "pending",
        "reasoning": "Property is in a rapidly appreciating area. Need recent comps to make competitive offer.",
        "estimated_impact": "medium",
        "estimated_effort": "30 minutes",
        "due_date": "2025-11-13T12:00:00",
        "completed_at": None,
        "completed_by": None,
        "created_at": "2025-11-12T10:00:00"
    }
}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/smart-lists", response_model=List[SmartList])
def list_smart_lists():
    """
    List all smart lists.

    Returns all smart lists with their filter criteria and property counts.
    """
    return [
        SmartList(**smart_list)
        for smart_list in SMART_LISTS.values()
    ]


@router.post("/smart-lists", response_model=SmartList, status_code=201)
def create_smart_list(smart_list: SmartListCreate):
    """
    Create a new smart list.

    Smart lists dynamically filter properties based on criteria.
    The property count is automatically calculated.
    """
    import random

    # Generate new ID
    new_id = f"sl_{str(len(SMART_LISTS) + 1).zfill(3)}"

    # Calculate mock property count based on filter complexity
    property_count = random.randint(5, 100)

    new_smart_list = {
        "id": new_id,
        "name": smart_list.name,
        "description": smart_list.description,
        "filters": [f.dict() for f in smart_list.filters],
        "tags": smart_list.tags or [],
        "property_count": property_count,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    SMART_LISTS[new_id] = new_smart_list

    return SmartList(**new_smart_list)


@router.get("/smart-lists/{smart_list_id}", response_model=SmartList)
def get_smart_list(smart_list_id: str):
    """
    Get details of a specific smart list.

    Returns the smart list configuration and current property count.
    """
    if smart_list_id not in SMART_LISTS:
        raise HTTPException(status_code=404, detail="Smart list not found")

    return SmartList(**SMART_LISTS[smart_list_id])


@router.patch("/smart-lists/{smart_list_id}", response_model=SmartList)
def update_smart_list(smart_list_id: str, update: SmartListUpdate):
    """
    Update a smart list.

    Allows updating name, description, filters, and tags.
    Property count is recalculated automatically.
    """
    if smart_list_id not in SMART_LISTS:
        raise HTTPException(status_code=404, detail="Smart list not found")

    smart_list = SMART_LISTS[smart_list_id]

    # Update fields
    if update.name is not None:
        smart_list["name"] = update.name
    if update.description is not None:
        smart_list["description"] = update.description
    if update.filters is not None:
        smart_list["filters"] = [f.dict() for f in update.filters]
        # Recalculate property count when filters change
        import random
        smart_list["property_count"] = random.randint(5, 100)
    if update.tags is not None:
        smart_list["tags"] = update.tags

    smart_list["updated_at"] = datetime.now().isoformat()

    return SmartList(**smart_list)


@router.delete("/smart-lists/{smart_list_id}", status_code=204)
def delete_smart_list(smart_list_id: str):
    """
    Delete a smart list.

    Removes the smart list from the system.
    """
    if smart_list_id not in SMART_LISTS:
        raise HTTPException(status_code=404, detail="Smart list not found")

    del SMART_LISTS[smart_list_id]
    return None


@router.get("/smart-lists/{smart_list_id}/properties", response_model=List[PropertySummary])
def get_smart_list_properties(smart_list_id: str, limit: int = 50, offset: int = 0):
    """
    Get properties matching a smart list.

    Returns properties that match the smart list filter criteria.
    Results are paginated.
    """
    if smart_list_id not in SMART_LISTS:
        raise HTTPException(status_code=404, detail="Smart list not found")

    # Mock properties matching the smart list
    mock_properties = [
        PropertySummary(
            id="prop_001",
            address="1234 Market St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            property_type="single_family",
            status="off_market",
            estimated_value=875000.0,
            score=0.82,
            owner_name="John Smith",
            last_contact="2025-11-10T14:30:00"
        ),
        PropertySummary(
            id="prop_002",
            address="5678 Mission St",
            city="San Francisco",
            state="CA",
            zip_code="94110",
            property_type="multi_family",
            status="off_market",
            estimated_value=1250000.0,
            score=0.78,
            owner_name="Jane Doe",
            last_contact=None
        ),
        PropertySummary(
            id="prop_003",
            address="9012 Valencia St",
            city="San Francisco",
            state="CA",
            zip_code="94110",
            property_type="condo",
            status="active",
            estimated_value=625000.0,
            score=0.65,
            owner_name="Bob Johnson",
            last_contact="2025-11-05T09:15:00"
        ),
    ]

    # Apply pagination
    return mock_properties[offset:offset + limit]


@router.post("/next-best-actions/generate", response_model=NextBestAction, status_code=201)
def generate_next_best_action(request: NextBestActionGenerate):
    """
    Generate a Next-Best-Action for a property.

    Uses AI/rules to recommend the optimal next action to take
    for a property based on its current state and context.
    """
    import random

    # Mock NBA generation based on property context
    action_types = [
        {
            "action_type": "email",
            "title": "Send personalized outreach email",
            "description": "Craft and send initial contact email to property owner",
            "priority": "high",
            "reasoning": "Property shows strong distress signals. Owner likely motivated to sell.",
            "estimated_impact": "high",
            "estimated_effort": "10 minutes"
        },
        {
            "action_type": "call",
            "title": "Make introduction phone call",
            "description": "Call owner to introduce yourself and gauge interest",
            "priority": "medium",
            "reasoning": "Property has been on your list for 30 days without contact.",
            "estimated_impact": "medium",
            "estimated_effort": "15 minutes"
        },
        {
            "action_type": "research",
            "title": "Analyze comparable sales",
            "description": "Research recent sales in the area to determine fair offer price",
            "priority": "medium",
            "reasoning": "Need market data to make competitive offer.",
            "estimated_impact": "medium",
            "estimated_effort": "30 minutes"
        },
        {
            "action_type": "visit",
            "title": "Schedule property walk-through",
            "description": "Arrange in-person visit to assess property condition",
            "priority": "low",
            "reasoning": "Owner has expressed interest. Time for physical inspection.",
            "estimated_impact": "high",
            "estimated_effort": "2 hours"
        }
    ]

    action_template = random.choice(action_types)

    # Generate new ID
    new_id = f"nba_{str(len(NEXT_BEST_ACTIONS) + 1).zfill(3)}"

    new_nba = {
        "id": new_id,
        "property_id": request.property_id,
        "action_type": action_template["action_type"],
        "title": action_template["title"],
        "description": action_template["description"],
        "priority": action_template["priority"],
        "status": "pending",
        "reasoning": action_template["reasoning"],
        "estimated_impact": action_template["estimated_impact"],
        "estimated_effort": action_template["estimated_effort"],
        "due_date": (datetime.now().replace(hour=17, minute=0, second=0)
                     + timedelta(days=random.randint(1, 7))).isoformat(),
        "completed_at": None,
        "completed_by": None,
        "created_at": datetime.now().isoformat()
    }

    NEXT_BEST_ACTIONS[new_id] = new_nba

    return NextBestAction(**new_nba)


@router.get("/next-best-actions", response_model=List[NextBestAction])
def list_next_best_actions(
    property_id: Optional[str] = None,
    status: Optional[NBAStatus] = None,
    priority: Optional[NBAPriority] = None
):
    """
    List Next-Best-Actions with optional filters.

    Filter by property, status, or priority to find relevant actions.
    """
    nbas = list(NEXT_BEST_ACTIONS.values())

    # Apply filters
    if property_id:
        nbas = [nba for nba in nbas if nba["property_id"] == property_id]
    if status:
        nbas = [nba for nba in nbas if nba["status"] == status.value]
    if priority:
        nbas = [nba for nba in nbas if nba["priority"] == priority.value]

    return [NextBestAction(**nba) for nba in nbas]


@router.get("/next-best-actions/{nba_id}", response_model=NextBestAction)
def get_next_best_action(nba_id: str):
    """
    Get details of a specific Next-Best-Action.
    """
    if nba_id not in NEXT_BEST_ACTIONS:
        raise HTTPException(status_code=404, detail="Next-Best-Action not found")

    return NextBestAction(**NEXT_BEST_ACTIONS[nba_id])


@router.post("/next-best-actions/{nba_id}/complete", response_model=NextBestAction)
def complete_next_best_action(nba_id: str, completion: NBAComplete):
    """
    Mark a Next-Best-Action as complete.

    Records completion time, user, and optional notes/outcome.
    """
    if nba_id not in NEXT_BEST_ACTIONS:
        raise HTTPException(status_code=404, detail="Next-Best-Action not found")

    nba = NEXT_BEST_ACTIONS[nba_id]

    if nba["status"] == "completed":
        raise HTTPException(status_code=400, detail="Action is already completed")

    nba["status"] = "completed"
    nba["completed_at"] = datetime.now().isoformat()
    nba["completed_by"] = "demo@realestateos.com"

    # Store notes/outcome if provided (could be added to schema)
    if completion.notes:
        nba["completion_notes"] = completion.notes
    if completion.outcome:
        nba["outcome"] = completion.outcome

    return NextBestAction(**nba)


@router.post("/next-best-actions/{nba_id}/dismiss", response_model=NextBestAction)
def dismiss_next_best_action(nba_id: str):
    """
    Dismiss a Next-Best-Action without completing it.

    Marks the action as not relevant or not needed.
    """
    if nba_id not in NEXT_BEST_ACTIONS:
        raise HTTPException(status_code=404, detail="Next-Best-Action not found")

    nba = NEXT_BEST_ACTIONS[nba_id]
    nba["status"] = "dismissed"

    return NextBestAction(**nba)


# Import timedelta for NBA due dates
from datetime import timedelta
