"""
Sharing & Deal Rooms Router
Secure Share Links, Room artifacts - Zero-friction collaboration
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import string

from api.database import get_db
from api import schemas
from db.models import (
    Property, ShareLink, ShareLinkView, ShareLinkStatus,
    DealRoom, DealRoomArtifact, InvestorReadinessLevel
)

router = APIRouter(prefix="/sharing", tags=["Sharing & Collaboration"])

# ============================================================================
# SECURE SHARE LINKS
# ============================================================================

def generate_short_code(length: int = 8) -> str:
    """Generate a random short code for share links"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.post("/share-links", response_model=schemas.ShareLinkResponse, status_code=201)
def create_share_link(
    link_data: schemas.ShareLinkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a secure share link for memo or deal room

    Features:
    - No login required
    - Optional password protection
    - Watermarking
    - Link expiry
    - View limits
    - Per-viewer tracking

    Perfect for sharing with investors without friction

    KPI: Investor engagement (views, questions) and time to offer
    """
    # Validate that either property_id or deal_room_id is provided
    if not link_data.property_id and not link_data.deal_room_id:
        raise HTTPException(status_code=400, detail="Must provide either property_id or deal_room_id")

    # Generate unique short code
    short_code = generate_short_code()
    while db.query(ShareLink).filter(ShareLink.short_code == short_code).first():
        short_code = generate_short_code()

    # Create share link
    share_link = ShareLink(
        property_id=link_data.property_id,
        deal_room_id=link_data.deal_room_id,
        short_code=short_code,
        status=ShareLinkStatus.ACTIVE,
        password_hash=link_data.password_hash,
        watermark_text=link_data.watermark_text or "Confidential",
        expires_at=link_data.expires_at,
        max_views=link_data.max_views,
        viewer_name=link_data.viewer_name,
        viewer_email=link_data.viewer_email,
        created_by_user_id=link_data.created_by_user_id
    )

    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    return share_link

@router.get("/share-links/{short_code}", response_model=schemas.ShareLinkResponse)
def get_share_link_by_code(
    short_code: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Access a share link by short code

    Checks:
    - Link exists
    - Not expired
    - Not revoked
    - Within view limits
    - Password matches (if protected)
    """
    # Get share link
    share_link = db.query(ShareLink).filter(ShareLink.short_code == short_code).first()
    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Check status
    if share_link.status != ShareLinkStatus.ACTIVE:
        raise HTTPException(status_code=403, detail=f"Link is {share_link.status.value}")

    # Check expiry
    if share_link.expires_at and share_link.expires_at < datetime.utcnow():
        share_link.status = ShareLinkStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=403, detail="Link has expired")

    # Check view limit
    if share_link.max_views and share_link.view_count >= share_link.max_views:
        share_link.status = ShareLinkStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=403, detail="View limit reached")

    # Check password (simplified - in production, use proper password hashing)
    if share_link.password_hash and password != share_link.password_hash:
        raise HTTPException(status_code=403, detail="Invalid password")

    return share_link

@router.post("/share-links/{short_code}/track-view")
def track_share_link_view(
    short_code: str,
    viewer_ip: Optional[str] = None,
    viewer_user_agent: Optional[str] = None,
    time_spent_seconds: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Track a view of a share link

    Records:
    - Timestamp
    - Viewer IP
    - User agent
    - Time spent
    - Pages viewed

    KPI: Investor engagement tracking
    """
    # Get share link
    share_link = db.query(ShareLink).filter(ShareLink.short_code == short_code).first()
    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Create view record
    view = ShareLinkView(
        share_link_id=share_link.id,
        viewer_ip=viewer_ip,
        viewer_user_agent=viewer_user_agent,
        time_spent_seconds=time_spent_seconds
    )

    db.add(view)

    # Update share link
    share_link.view_count += 1
    share_link.last_viewed_at = datetime.utcnow()

    db.commit()

    return {"status": "tracked", "view_count": share_link.view_count}

@router.post("/share-links/{link_id}/revoke")
def revoke_share_link(
    link_id: int,
    db: Session = Depends(get_db)
):
    """
    Revoke a share link (disable access)
    """
    share_link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    share_link.status = ShareLinkStatus.REVOKED

    db.commit()

    return {"status": "revoked"}

@router.get("/share-links/{link_id}/analytics")
def get_share_link_analytics(
    link_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a share link

    Returns:
    - Total views
    - Unique viewers (by IP)
    - Average time spent
    - View timeline
    """
    share_link = db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not share_link:
        raise HTTPException(status_code=404, detail="Share link not found")

    # Get all views
    views = db.query(ShareLinkView).filter(ShareLinkView.share_link_id == link_id).all()

    # Calculate analytics
    unique_ips = len(set(v.viewer_ip for v in views if v.viewer_ip))
    avg_time_spent = sum(v.time_spent_seconds or 0 for v in views) / len(views) if views else 0

    return {
        "share_link_id": link_id,
        "short_code": share_link.short_code,
        "total_views": share_link.view_count,
        "unique_viewers": unique_ips,
        "avg_time_spent_seconds": avg_time_spent,
        "first_viewed_at": views[0].viewed_at if views else None,
        "last_viewed_at": share_link.last_viewed_at,
        "views_by_date": [
            {
                "viewed_at": v.viewed_at,
                "time_spent_seconds": v.time_spent_seconds,
                "viewer_ip": v.viewer_ip
            }
            for v in views
        ]
    }

# ============================================================================
# DEAL ROOMS
# ============================================================================

@router.post("/deal-rooms", response_model=schemas.DealRoomResponse, status_code=201)
def create_deal_room(
    room_data: schemas.DealRoomCreate,
    db: Session = Depends(get_db)
):
    """
    Create a Deal Room for property

    Deal Room = Central hub for:
    - Memos
    - Comps
    - Photos
    - Inspection reports
    - Disclosures

    Includes investor readiness scoring
    """
    # Get property
    property = db.query(Property).filter(Property.id == room_data.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Create deal room
    deal_room = DealRoom(
        property_id=room_data.property_id,
        name=room_data.name,
        description=room_data.description,
        readiness_level=InvestorReadinessLevel.RED,
        readiness_factors={}
    )

    db.add(deal_room)
    db.commit()
    db.refresh(deal_room)

    return deal_room

@router.get("/deal-rooms/{room_id}", response_model=schemas.DealRoomResponse)
def get_deal_room(room_id: int, db: Session = Depends(get_db)):
    """
    Get deal room with readiness score
    """
    deal_room = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not deal_room:
        raise HTTPException(status_code=404, detail="Deal room not found")

    return deal_room

@router.post("/deal-rooms/{room_id}/artifacts", response_model=schemas.DealRoomArtifactResponse, status_code=201)
def add_deal_room_artifact(
    room_id: int,
    artifact_data: schemas.DealRoomArtifactCreate,
    db: Session = Depends(get_db)
):
    """
    Add document/artifact to deal room

    Types:
    - memo: Investment memo PDF
    - comps: Comparable sales report
    - photos: Property photos
    - inspection: Inspection report
    - disclosure: Legal disclosures
    """
    # Get deal room
    deal_room = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not deal_room:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Create artifact
    artifact = DealRoomArtifact(
        deal_room_id=room_id,
        name=artifact_data.name,
        type=artifact_data.type,
        file_url=artifact_data.file_url,
        file_size=artifact_data.file_size,
        uploaded_by_user_id=artifact_data.uploaded_by_user_id
    )

    db.add(artifact)
    db.flush()

    # Update readiness factors
    _update_deal_room_readiness(db, deal_room)

    db.commit()
    db.refresh(artifact)

    return artifact

@router.get("/deal-rooms/{room_id}/artifacts", response_model=List[schemas.DealRoomArtifactResponse])
def list_deal_room_artifacts(room_id: int, db: Session = Depends(get_db)):
    """
    List all artifacts in deal room
    """
    artifacts = (
        db.query(DealRoomArtifact)
        .filter(DealRoomArtifact.deal_room_id == room_id)
        .order_by(desc(DealRoomArtifact.uploaded_at))
        .all()
    )

    return artifacts

@router.get("/deal-rooms/{room_id}/export")
def export_deal_room(room_id: int, db: Session = Depends(get_db)):
    """
    Export deal room as zipped "offer pack"

    Returns URL to download ZIP containing:
    - All artifacts
    - Manifest/index
    - Metadata

    Perfect for sending complete package to investors
    """
    deal_room = db.query(DealRoom).filter(DealRoom.id == room_id).first()
    if not deal_room:
        raise HTTPException(status_code=404, detail="Deal room not found")

    # Get all artifacts
    artifacts = db.query(DealRoomArtifact).filter(DealRoomArtifact.deal_room_id == room_id).all()

    # In production, this would actually create a ZIP file
    # For now, return metadata
    export_url = f"https://exports.real-estate-os.com/deal-rooms/{room_id}/offer-pack.zip"

    return {
        "deal_room_id": room_id,
        "export_url": export_url,
        "artifacts_count": len(artifacts),
        "artifact_types": list(set(a.type for a in artifacts)),
        "total_size_bytes": sum(a.file_size or 0 for a in artifacts)
    }

def _update_deal_room_readiness(db: Session, deal_room: DealRoom):
    """
    Update deal room readiness based on artifacts present

    RED: Missing critical items
    YELLOW: Has basics, missing nice-to-haves
    GREEN: Complete and ready to share
    """
    # Get artifacts by type
    artifacts = db.query(DealRoomArtifact).filter(DealRoomArtifact.deal_room_id == deal_room.id).all()
    artifact_types = set(a.type for a in artifacts)

    # Check readiness factors
    factors = {
        "has_memo": "memo" in artifact_types,
        "has_comps": "comps" in artifact_types,
        "has_photos": "photos" in artifact_types,
        "has_inspection": "inspection" in artifact_types,
        "has_disclosures": "disclosure" in artifact_types
    }

    # Critical items
    critical = ["has_memo", "has_comps"]
    critical_complete = all(factors[key] for key in critical)

    # Nice to have
    nice_to_have = ["has_photos", "has_inspection", "has_disclosures"]
    nice_to_have_count = sum(factors[key] for key in nice_to_have)

    # Determine readiness level
    if not critical_complete:
        deal_room.readiness_level = InvestorReadinessLevel.RED
    elif nice_to_have_count >= 2:
        deal_room.readiness_level = InvestorReadinessLevel.GREEN
    else:
        deal_room.readiness_level = InvestorReadinessLevel.YELLOW

    deal_room.readiness_factors = factors
    deal_room.updated_at = datetime.utcnow()
