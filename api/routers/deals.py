"""Deal and Portfolio router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import (
    User,
    Deal,
    Transaction,
    Portfolio,
    Property,
    Lead,
)
from ..models.deal import DealStage, DealType, TransactionType
from ..schemas.deal import (
    DealCreate,
    DealUpdate,
    DealResponse,
    DealListResponse,
    DealStats,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    PortfolioDetailResponse,
    PortfolioListResponse,
    PortfolioStats,
)


router = APIRouter(prefix="/deals", tags=["deals"])
portfolio_router = APIRouter(prefix="/portfolios", tags=["portfolios"])


# ================== DEAL ENDPOINTS ==================

@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    deal: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:create")),
):
    """Create a new deal."""
    # Verify property exists and belongs to organization
    property_obj = db.query(Property).filter(
        Property.id == deal.property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Verify lead if provided
    if deal.lead_id:
        lead = db.query(Lead).filter(
            Lead.id == deal.lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        ).first()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

    # Verify assigned user if provided
    if deal.assigned_to:
        assigned_user = db.query(User).filter(
            User.id == deal.assigned_to,
            User.organization_id == current_user.organization_id,
        ).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    # Create deal
    db_deal = Deal(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **deal.model_dump(),
    )

    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)

    return db_deal


@router.get("", response_model=DealListResponse)
def list_deals(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    deal_type: Optional[DealType] = None,
    stage: Optional[DealStage] = None,
    assigned_to: Optional[int] = None,
    min_value: Optional[Decimal] = None,
    max_value: Optional[Decimal] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:read")),
):
    """List deals with filtering and pagination."""
    query = db.query(Deal).filter(
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    )

    # Apply filters
    if deal_type:
        query = query.filter(Deal.deal_type == deal_type)

    if stage:
        query = query.filter(Deal.stage == stage)

    if assigned_to:
        query = query.filter(Deal.assigned_to == assigned_to)

    if min_value is not None:
        query = query.filter(Deal.value >= min_value)

    if max_value is not None:
        query = query.filter(Deal.value <= max_value)

    if search:
        query = query.filter(
            or_(
                Deal.notes.ilike(f"%{search}%"),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    deals = query.order_by(Deal.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": deals,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/stats", response_model=DealStats)
def get_deal_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:read")),
):
    """Get deal statistics."""
    query = db.query(Deal).filter(
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    )

    if start_date:
        query = query.filter(Deal.created_at >= start_date)

    if end_date:
        query = query.filter(Deal.created_at <= end_date)

    deals = query.all()

    total_deals = len(deals)
    total_value = sum(deal.value for deal in deals)
    avg_deal_value = total_value / total_deals if total_deals > 0 else Decimal("0")

    won_deals = sum(1 for deal in deals if deal.stage == DealStage.CLOSED_WON)
    lost_deals = sum(1 for deal in deals if deal.stage == DealStage.CLOSED_LOST)
    closed_deals = won_deals + lost_deals
    win_rate = (won_deals / closed_deals * 100) if closed_deals > 0 else 0.0

    # Group by stage
    by_stage = {}
    for stage in DealStage:
        count = sum(1 for deal in deals if deal.stage == stage)
        by_stage[stage.value] = count

    # Group by type
    by_type = {}
    for deal_type in DealType:
        count = sum(1 for deal in deals if deal.deal_type == deal_type)
        by_type[deal_type.value] = count

    return {
        "total_deals": total_deals,
        "total_value": total_value,
        "avg_deal_value": avg_deal_value,
        "won_deals": won_deals,
        "lost_deals": lost_deals,
        "win_rate": win_rate,
        "by_stage": by_stage,
        "by_type": by_type,
    }


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:read")),
):
    """Get a specific deal."""
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    ).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    return deal


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    deal_update: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:update")),
):
    """Update a deal."""
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    ).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # Verify lead if being updated
    if deal_update.lead_id is not None:
        lead = db.query(Lead).filter(
            Lead.id == deal_update.lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        ).first()

        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead not found",
            )

    # Verify assigned user if being updated
    if deal_update.assigned_to is not None:
        assigned_user = db.query(User).filter(
            User.id == deal_update.assigned_to,
            User.organization_id == current_user.organization_id,
        ).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    # Update deal
    update_data = deal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deal, field, value)

    deal.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(deal)

    return deal


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("deal:delete")),
):
    """Soft delete a deal."""
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    ).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    deal.deleted_at = datetime.utcnow()
    db.commit()


# ================== TRANSACTION ENDPOINTS ==================

@router.post("/{deal_id}/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    deal_id: int,
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("transaction:create")),
):
    """Create a transaction for a deal."""
    # Verify deal exists
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    ).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # Verify transaction belongs to this deal
    if transaction.deal_id != deal_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction deal_id must match URL deal_id",
        )

    # Create transaction
    db_transaction = Transaction(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **transaction.model_dump(),
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return db_transaction


@router.get("/{deal_id}/transactions", response_model=TransactionListResponse)
def list_transactions(
    deal_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    transaction_type: Optional[TransactionType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("transaction:read")),
):
    """List transactions for a deal."""
    # Verify deal exists
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.organization_id == current_user.organization_id,
        Deal.deleted_at.is_(None),
    ).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    query = db.query(Transaction).filter(
        Transaction.deal_id == deal_id,
        Transaction.organization_id == current_user.organization_id,
    )

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    total = query.count()

    offset = (page - 1) * page_size
    transactions = query.order_by(Transaction.transaction_date.desc()).offset(offset).limit(page_size).all()

    return {
        "items": transactions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


# ================== PORTFOLIO ENDPOINTS ==================

@portfolio_router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:create")),
):
    """Create a new portfolio."""
    # Create portfolio
    db_portfolio = Portfolio(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        name=portfolio.name,
        description=portfolio.description,
        metadata=portfolio.metadata,
    )

    db.add(db_portfolio)
    db.flush()

    # Add properties if provided
    if portfolio.property_ids:
        properties = db.query(Property).filter(
            Property.id.in_(portfolio.property_ids),
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        ).all()

        if len(properties) != len(portfolio.property_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more properties not found",
            )

        db_portfolio.properties = properties

    db.commit()
    db.refresh(db_portfolio)

    # Calculate stats
    db_portfolio.property_count = len(db_portfolio.properties)
    db_portfolio.total_value = sum(p.price for p in db_portfolio.properties if p.price)

    return db_portfolio


@portfolio_router.get("", response_model=PortfolioListResponse)
def list_portfolios(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:read")),
):
    """List portfolios with filtering and pagination."""
    query = db.query(Portfolio).filter(
        Portfolio.organization_id == current_user.organization_id,
    )

    if search:
        query = query.filter(
            or_(
                Portfolio.name.ilike(f"%{search}%"),
                Portfolio.description.ilike(f"%{search}%"),
            )
        )

    total = query.count()

    offset = (page - 1) * page_size
    portfolios = query.order_by(Portfolio.created_at.desc()).offset(offset).limit(page_size).all()

    # Calculate stats for each portfolio
    for portfolio in portfolios:
        portfolio.property_count = len(portfolio.properties)
        portfolio.total_value = sum(p.price for p in portfolio.properties if p.price)

    return {
        "items": portfolios,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@portfolio_router.get("/stats", response_model=PortfolioStats)
def get_portfolio_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:read")),
):
    """Get portfolio statistics."""
    portfolios = db.query(Portfolio).filter(
        Portfolio.organization_id == current_user.organization_id,
    ).all()

    total_portfolios = len(portfolios)
    total_properties = sum(len(p.properties) for p in portfolios)
    total_value = sum(
        sum(prop.price for prop in p.properties if prop.price)
        for p in portfolios
    )
    avg_portfolio_value = total_value / total_portfolios if total_portfolios > 0 else Decimal("0")

    return {
        "total_portfolios": total_portfolios,
        "total_properties": total_properties,
        "total_value": total_value,
        "avg_portfolio_value": avg_portfolio_value,
    }


@portfolio_router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:read")),
):
    """Get a specific portfolio with properties."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.organization_id == current_user.organization_id,
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Calculate stats
    portfolio.property_count = len(portfolio.properties)
    portfolio.total_value = sum(p.price for p in portfolio.properties if p.price)

    # Convert properties to dict
    properties_data = []
    for prop in portfolio.properties:
        properties_data.append({
            "id": prop.id,
            "address": prop.address,
            "city": prop.city,
            "state": prop.state,
            "zip_code": prop.zip_code,
            "property_type": prop.property_type,
            "price": prop.price,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "square_feet": prop.square_feet,
        })

    response_data = {
        **portfolio.__dict__,
        "properties": properties_data,
    }

    return response_data


@portfolio_router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: int,
    portfolio_update: PortfolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:update")),
):
    """Update a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.organization_id == current_user.organization_id,
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Update portfolio
    update_data = portfolio_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(portfolio, field, value)

    portfolio.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(portfolio)

    # Calculate stats
    portfolio.property_count = len(portfolio.properties)
    portfolio.total_value = sum(p.price for p in portfolio.properties if p.price)

    return portfolio


@portfolio_router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:delete")),
):
    """Delete a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.organization_id == current_user.organization_id,
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    db.delete(portfolio)
    db.commit()


@portfolio_router.post("/{portfolio_id}/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_property_to_portfolio(
    portfolio_id: int,
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:update")),
):
    """Add a property to a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.organization_id == current_user.organization_id,
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Check if already in portfolio
    if property_obj in portfolio.properties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property already in portfolio",
        )

    portfolio.properties.append(property_obj)
    portfolio.updated_at = datetime.utcnow()

    db.commit()


@portfolio_router.delete("/{portfolio_id}/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_property_from_portfolio(
    portfolio_id: int,
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("portfolio:update")),
):
    """Remove a property from a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.organization_id == current_user.organization_id,
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Check if in portfolio
    if property_obj not in portfolio.properties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property not in portfolio",
        )

    portfolio.properties.remove(property_obj)
    portfolio.updated_at = datetime.utcnow()

    db.commit()
