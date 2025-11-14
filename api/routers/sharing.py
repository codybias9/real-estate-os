"""Sharing router for share links, deal rooms, and collaboration features."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random
import secrets

router = APIRouter(prefix="/sharing", tags=["sharing"])


# ============================================================================
# Enums
# ============================================================================

class ShareLinkPermission(str, Enum):
    """Permission level for share links."""
    view_only = "view_only"
    comment = "comment"
    edit = "edit"


class DealRoomStatus(str, Enum):
    """Status of a deal room."""
    active = "active"
    archived = "archived"
    closed = "closed"


class ArtifactType(str, Enum):
    """Type of artifact in a deal room."""
    document = "document"
    image = "image"
    spreadsheet = "spreadsheet"
    presentation = "presentation"
    video = "video"
    other = "other"


# ============================================================================
# Schemas
# ============================================================================

class ShareLinkCreate(BaseModel):
    """Request to create a share link."""
    resource_type: str = Field(..., description="Type of resource (property, deal_room, document)")
    resource_id: str = Field(..., description="ID of the resource to share")
    permission: ShareLinkPermission = ShareLinkPermission.view_only
    expires_at: Optional[str] = Field(
        None,
        description="ISO datetime when link expires (null = never expires)"
    )
    password_protected: bool = False
    password: Optional[str] = None
    allow_download: bool = True
    max_views: Optional[int] = Field(None, description="Max number of views (null = unlimited)")


class ShareLink(BaseModel):
    """Share link response."""
    id: str
    resource_type: str
    resource_id: str
    link_url: str
    permission: ShareLinkPermission
    expires_at: Optional[str]
    password_protected: bool
    allow_download: bool
    max_views: Optional[int]
    current_views: int
    is_active: bool
    created_at: str
    created_by: str


class DealRoomCreate(BaseModel):
    """Request to create a deal room."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    property_id: str
    participants: List[EmailStr] = Field(default_factory=list)
    tags: Optional[List[str]] = []


class DealRoom(BaseModel):
    """Deal room response."""
    id: str
    name: str
    description: Optional[str]
    property_id: str
    status: DealRoomStatus
    participants: List[str]
    artifact_count: int
    last_activity: str
    tags: List[str]
    created_at: str
    created_by: str


class ArtifactUpload(BaseModel):
    """Request to upload an artifact to a deal room."""
    name: str = Field(..., min_length=1)
    artifact_type: ArtifactType
    file_url: str = Field(..., description="URL where file is stored (S3, MinIO, etc.)")
    file_size: int = Field(..., description="File size in bytes")
    description: Optional[str] = None
    tags: Optional[List[str]] = []


class Artifact(BaseModel):
    """Artifact in a deal room."""
    id: str
    deal_room_id: str
    name: str
    artifact_type: ArtifactType
    file_url: str
    file_size: int
    description: Optional[str]
    tags: List[str]
    uploaded_by: str
    uploaded_at: str
    view_count: int
    download_count: int


class DealRoomParticipant(BaseModel):
    """Participant in a deal room."""
    email: EmailStr
    name: Optional[str]
    role: str = Field(description="buyer, seller, agent, attorney, inspector, etc.")
    added_at: str


# ============================================================================
# Mock Data Store
# ============================================================================

SHARE_LINKS: Dict[str, Dict] = {
    "link_001": {
        "id": "link_001",
        "resource_type": "property",
        "resource_id": "prop_001",
        "link_url": "https://app.realestateos.com/shared/abc123def456",
        "permission": "view_only",
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "password_protected": False,
        "allow_download": True,
        "max_views": None,
        "current_views": 12,
        "is_active": True,
        "created_at": "2025-11-01T10:00:00",
        "created_by": "demo@realestateos.com"
    },
    "link_002": {
        "id": "link_002",
        "resource_type": "deal_room",
        "resource_id": "room_001",
        "link_url": "https://app.realestateos.com/shared/xyz789ghi012",
        "permission": "comment",
        "expires_at": None,
        "password_protected": True,
        "allow_download": False,
        "max_views": 50,
        "current_views": 23,
        "is_active": True,
        "created_at": "2025-10-15T14:30:00",
        "created_by": "demo@realestateos.com"
    }
}

DEAL_ROOMS: Dict[str, Dict] = {
    "room_001": {
        "id": "room_001",
        "name": "1234 Market St - Purchase Deal",
        "description": "Deal room for purchase of 1234 Market St property",
        "property_id": "prop_001",
        "status": "active",
        "participants": [
            "demo@realestateos.com",
            "john.smith@example.com",
            "attorney@lawfirm.com",
            "inspector@inspections.com"
        ],
        "artifact_count": 8,
        "last_activity": "2025-11-12T09:30:00",
        "tags": ["purchase", "commercial"],
        "created_at": "2025-10-20T11:00:00",
        "created_by": "demo@realestateos.com"
    },
    "room_002": {
        "id": "room_002",
        "name": "5678 Mission St - Due Diligence",
        "description": "Due diligence phase for multi-family property",
        "property_id": "prop_002",
        "status": "active",
        "participants": [
            "demo@realestateos.com",
            "jane.doe@example.com",
            "cpa@accounting.com"
        ],
        "artifact_count": 15,
        "last_activity": "2025-11-11T16:45:00",
        "tags": ["due-diligence", "multi-family"],
        "created_at": "2025-10-25T09:00:00",
        "created_by": "demo@realestateos.com"
    },
    "room_003": {
        "id": "room_003",
        "name": "9012 Valencia St - Closed",
        "description": "Completed purchase transaction",
        "property_id": "prop_003",
        "status": "closed",
        "participants": [
            "demo@realestateos.com",
            "bob.johnson@example.com"
        ],
        "artifact_count": 23,
        "last_activity": "2025-10-30T15:00:00",
        "tags": ["closed", "single-family"],
        "created_at": "2025-09-15T10:00:00",
        "created_by": "demo@realestateos.com"
    }
}

ARTIFACTS: Dict[str, Dict] = {
    "art_001": {
        "id": "art_001",
        "deal_room_id": "room_001",
        "name": "Purchase Agreement - Draft.pdf",
        "artifact_type": "document",
        "file_url": "s3://deal-rooms/room_001/purchase_agreement_draft.pdf",
        "file_size": 245678,
        "description": "Initial draft of purchase agreement",
        "tags": ["legal", "draft"],
        "uploaded_by": "demo@realestateos.com",
        "uploaded_at": "2025-10-21T10:00:00",
        "view_count": 15,
        "download_count": 4
    },
    "art_002": {
        "id": "art_002",
        "deal_room_id": "room_001",
        "name": "Property Inspection Report.pdf",
        "artifact_type": "document",
        "file_url": "s3://deal-rooms/room_001/inspection_report.pdf",
        "file_size": 1234567,
        "description": "Full property inspection with photos",
        "tags": ["inspection", "due-diligence"],
        "uploaded_by": "inspector@inspections.com",
        "uploaded_at": "2025-10-25T14:30:00",
        "view_count": 8,
        "download_count": 3
    },
    "art_003": {
        "id": "art_003",
        "deal_room_id": "room_001",
        "name": "Property Photos.zip",
        "artifact_type": "image",
        "file_url": "s3://deal-rooms/room_001/photos.zip",
        "file_size": 45678901,
        "description": "High-resolution property photos",
        "tags": ["photos", "marketing"],
        "uploaded_by": "demo@realestateos.com",
        "uploaded_at": "2025-10-22T09:00:00",
        "view_count": 22,
        "download_count": 7
    }
}


# ============================================================================
# Share Link Endpoints
# ============================================================================

@router.get("/share-links", response_model=List[ShareLink])
def list_share_links(resource_type: Optional[str] = None, active_only: bool = True):
    """
    List all share links.

    Can filter by resource type and active status.
    """
    links = list(SHARE_LINKS.values())

    if resource_type:
        links = [link for link in links if link["resource_type"] == resource_type]

    if active_only:
        now = datetime.now()
        links = [
            link for link in links
            if link["is_active"] and (
                link["expires_at"] is None or
                datetime.fromisoformat(link["expires_at"]) > now
            )
        ]

    return [ShareLink(**link) for link in links]


@router.post("/share-links", response_model=ShareLink, status_code=201)
def create_share_link(link_request: ShareLinkCreate):
    """
    Create a new share link.

    Generates a unique, secure link to share a resource externally.
    Can set expiration, password protection, view limits, and permissions.
    """
    # Generate unique link ID and URL
    link_id = f"link_{str(len(SHARE_LINKS) + 1).zfill(3)}"
    token = secrets.token_urlsafe(16)
    link_url = f"https://app.realestateos.com/shared/{token}"

    new_link = {
        "id": link_id,
        "resource_type": link_request.resource_type,
        "resource_id": link_request.resource_id,
        "link_url": link_url,
        "permission": link_request.permission.value,
        "expires_at": link_request.expires_at,
        "password_protected": link_request.password_protected,
        "allow_download": link_request.allow_download,
        "max_views": link_request.max_views,
        "current_views": 0,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    # Store password separately (would be hashed in real system)
    if link_request.password_protected and link_request.password:
        # In real system, hash password and store securely
        pass

    SHARE_LINKS[link_id] = new_link

    return ShareLink(**new_link)


@router.get("/share-links/{link_id}", response_model=ShareLink)
def get_share_link(link_id: str):
    """
    Get details of a specific share link.
    """
    if link_id not in SHARE_LINKS:
        raise HTTPException(status_code=404, detail="Share link not found")

    return ShareLink(**SHARE_LINKS[link_id])


@router.delete("/share-links/{link_id}", status_code=204)
def revoke_share_link(link_id: str):
    """
    Revoke a share link.

    Deactivates the link immediately. Link URL will no longer work.
    """
    if link_id not in SHARE_LINKS:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Mark as inactive rather than delete (for audit trail)
    SHARE_LINKS[link_id]["is_active"] = False

    return None


@router.get("/share-links/{link_id}/analytics")
def get_share_link_analytics(link_id: str):
    """
    Get analytics for a share link.

    Shows view count, download count, and access history.
    """
    if link_id not in SHARE_LINKS:
        raise HTTPException(status_code=404, detail="Share link not found")

    link = SHARE_LINKS[link_id]

    # Mock analytics data
    return {
        "link_id": link_id,
        "total_views": link["current_views"],
        "unique_visitors": random.randint(int(link["current_views"] * 0.6), link["current_views"]),
        "downloads": random.randint(0, link["current_views"] // 3),
        "last_accessed": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
        "access_by_country": {
            "US": random.randint(5, 10),
            "UK": random.randint(1, 3),
            "CA": random.randint(1, 2)
        },
        "access_by_device": {
            "desktop": random.randint(5, 10),
            "mobile": random.randint(2, 5),
            "tablet": random.randint(0, 2)
        }
    }


# ============================================================================
# Deal Room Endpoints
# ============================================================================

@router.get("/deal-rooms", response_model=List[DealRoom])
def list_deal_rooms(
    property_id: Optional[str] = None,
    status: Optional[DealRoomStatus] = None
):
    """
    List all deal rooms.

    Can filter by property or status.
    """
    rooms = list(DEAL_ROOMS.values())

    if property_id:
        rooms = [room for room in rooms if room["property_id"] == property_id]

    if status:
        rooms = [room for room in rooms if room["status"] == status.value]

    # Sort by last activity (most recent first)
    rooms.sort(key=lambda r: r["last_activity"], reverse=True)

    return [DealRoom(**room) for room in rooms]


@router.post("/deal-rooms", response_model=DealRoom, status_code=201)
def create_deal_room(room_request: DealRoomCreate):
    """
    Create a new deal room.

    Deal rooms are collaborative spaces for managing transactions.
    Automatically adds creator as a participant.
    """
    # Generate new ID
    room_id = f"room_{str(len(DEAL_ROOMS) + 1).zfill(3)}"

    # Add creator to participants
    participants = list(room_request.participants)
    if "demo@realestateos.com" not in participants:
        participants.insert(0, "demo@realestateos.com")

    new_room = {
        "id": room_id,
        "name": room_request.name,
        "description": room_request.description,
        "property_id": room_request.property_id,
        "status": "active",
        "participants": participants,
        "artifact_count": 0,
        "last_activity": datetime.now().isoformat(),
        "tags": room_request.tags or [],
        "created_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    DEAL_ROOMS[room_id] = new_room

    return DealRoom(**new_room)


@router.get("/deal-rooms/{room_id}", response_model=DealRoom)
def get_deal_room(room_id: str):
    """
    Get details of a specific deal room.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    return DealRoom(**DEAL_ROOMS[room_id])


@router.patch("/deal-rooms/{room_id}/status")
def update_deal_room_status(room_id: str, status: DealRoomStatus):
    """
    Update the status of a deal room.

    Can mark rooms as active, archived, or closed.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    DEAL_ROOMS[room_id]["status"] = status.value
    DEAL_ROOMS[room_id]["last_activity"] = datetime.now().isoformat()

    return {"room_id": room_id, "status": status.value}


@router.post("/deal-rooms/{room_id}/participants")
def add_participant(room_id: str, participant: DealRoomParticipant):
    """
    Add a participant to a deal room.

    Grants access to view and collaborate on deal room artifacts.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    room = DEAL_ROOMS[room_id]

    if participant.email not in room["participants"]:
        room["participants"].append(participant.email)
        room["last_activity"] = datetime.now().isoformat()

    return {
        "room_id": room_id,
        "participant_email": participant.email,
        "message": "Participant added successfully"
    }


@router.delete("/deal-rooms/{room_id}/participants/{email}")
def remove_participant(room_id: str, email: str):
    """
    Remove a participant from a deal room.

    Revokes access to the deal room.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    room = DEAL_ROOMS[room_id]

    if email in room["participants"]:
        room["participants"].remove(email)
        room["last_activity"] = datetime.now().isoformat()

    return {
        "room_id": room_id,
        "participant_email": email,
        "message": "Participant removed successfully"
    }


# ============================================================================
# Artifact Endpoints
# ============================================================================

@router.get("/deal-rooms/{room_id}/artifacts", response_model=List[Artifact])
def list_artifacts(room_id: str):
    """
    List all artifacts in a deal room.

    Returns documents, images, and other files uploaded to the room.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Get artifacts for this room
    room_artifacts = [
        Artifact(**artifact)
        for artifact in ARTIFACTS.values()
        if artifact["deal_room_id"] == room_id
    ]

    # Sort by upload date (most recent first)
    room_artifacts.sort(key=lambda a: a.uploaded_at, reverse=True)

    return room_artifacts


@router.post("/deal-rooms/{room_id}/artifacts", response_model=Artifact, status_code=201)
def upload_artifact(room_id: str, artifact: ArtifactUpload):
    """
    Upload an artifact to a deal room.

    In a real system, this would handle file upload to S3/MinIO.
    For demo, we accept the file_url directly.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Generate new ID
    artifact_id = f"art_{str(len(ARTIFACTS) + 1).zfill(3)}"

    new_artifact = {
        "id": artifact_id,
        "deal_room_id": room_id,
        "name": artifact.name,
        "artifact_type": artifact.artifact_type.value,
        "file_url": artifact.file_url,
        "file_size": artifact.file_size,
        "description": artifact.description,
        "tags": artifact.tags or [],
        "uploaded_by": "demo@realestateos.com",
        "uploaded_at": datetime.now().isoformat(),
        "view_count": 0,
        "download_count": 0
    }

    ARTIFACTS[artifact_id] = new_artifact

    # Update room artifact count and last activity
    DEAL_ROOMS[room_id]["artifact_count"] += 1
    DEAL_ROOMS[room_id]["last_activity"] = datetime.now().isoformat()

    return Artifact(**new_artifact)


@router.get("/deal-rooms/{room_id}/artifacts/{artifact_id}", response_model=Artifact)
def get_artifact(room_id: str, artifact_id: str):
    """
    Get details of a specific artifact.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    if artifact_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact = ARTIFACTS[artifact_id]

    if artifact["deal_room_id"] != room_id:
        raise HTTPException(status_code=404, detail="Artifact not found in this deal room")

    # Increment view count
    artifact["view_count"] += 1

    return Artifact(**artifact)


@router.delete("/deal-rooms/{room_id}/artifacts/{artifact_id}", status_code=204)
def delete_artifact(room_id: str, artifact_id: str):
    """
    Delete an artifact from a deal room.

    Removes the artifact metadata and file from storage.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    if artifact_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact = ARTIFACTS[artifact_id]

    if artifact["deal_room_id"] != room_id:
        raise HTTPException(status_code=404, detail="Artifact not found in this deal room")

    # Delete artifact
    del ARTIFACTS[artifact_id]

    # Update room artifact count
    DEAL_ROOMS[room_id]["artifact_count"] -= 1
    DEAL_ROOMS[room_id]["last_activity"] = datetime.now().isoformat()

    return None


@router.get("/deal-rooms/{room_id}/activity")
def get_deal_room_activity(room_id: str, limit: int = 50):
    """
    Get activity feed for a deal room.

    Shows recent actions like artifact uploads, participant additions, etc.
    """
    if room_id not in DEAL_ROOMS:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Mock activity feed
    activities = []
    base_time = datetime.now()

    activity_types = [
        {"type": "artifact_uploaded", "description": "uploaded {artifact_name}"},
        {"type": "participant_added", "description": "added {participant} to the room"},
        {"type": "comment_added", "description": "commented on {artifact_name}"},
        {"type": "artifact_downloaded", "description": "downloaded {artifact_name}"},
        {"type": "room_created", "description": "created the deal room"}
    ]

    for i in range(min(limit, 15)):
        activity = random.choice(activity_types)
        activities.append({
            "id": f"activity_{i+1}",
            "room_id": room_id,
            "type": activity["type"],
            "description": activity["description"].format(
                artifact_name="Purchase Agreement.pdf",
                participant="john.smith@example.com"
            ),
            "user": "demo@realestateos.com",
            "timestamp": (base_time - timedelta(hours=i * 3)).isoformat()
        })

    return activities
