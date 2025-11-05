"""User management router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import User, Role, Permission, UserRole, RolePermission
from ..schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    PermissionResponse,
)
from ..services.auth import AuthService

router = APIRouter(prefix="/users", tags=["user-management"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])
permissions_router = APIRouter(prefix="/permissions", tags=["permissions"])


# ================== USER ENDPOINTS ==================

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:create")),
):
    """Create a new user (admin only)."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password
    is_valid, error_message = AuthService.validate_password(user.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Create user
    hashed_password = AuthService.hash_password(user.password)
    db_user = User(
        organization_id=current_user.organization_id,
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        is_active=True,
        is_verified=True,  # Auto-verify admin-created users
    )

    db.add(db_user)
    db.flush()

    # Assign roles
    if user.role_ids:
        for role_id in user.role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                user_role = UserRole(user_id=db_user.id, role_id=role_id, assigned_by=current_user.id)
                db.add(user_role)

    db.commit()
    db.refresh(db_user)

    return db_user


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read")),
):
    """List users with filtering and pagination."""
    query = db.query(User).filter(
        User.organization_id == current_user.organization_id,
    )

    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
        )

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:read")),
):
    """Get a specific user."""
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:update")),
):
    """Update a user."""
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update user
    update_data = user_update.model_dump(exclude_unset=True, exclude={"role_ids"})
    for field, value in update_data.items():
        setattr(user, field, value)

    # Update roles if provided
    if user_update.role_ids is not None:
        # Remove existing roles
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()

        # Add new roles
        for role_id in user_update.role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                user_role = UserRole(user_id=user_id, role_id=role_id, assigned_by=current_user.id)
                db.add(user_role)

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete")),
):
    """Deactivate a user."""
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == current_user.organization_id,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Deactivate instead of delete
    user.is_active = False
    user.updated_at = datetime.utcnow()

    db.commit()


# ================== ROLE ENDPOINTS ==================

@roles_router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:create")),
):
    """Create a new role."""
    # Check if role already exists
    existing_role = db.query(Role).filter(Role.name == role.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    db_role = Role(
        name=role.name,
        description=role.description,
        is_system=False,
    )

    db.add(db_role)
    db.flush()

    # Assign permissions
    if role.permission_ids:
        for permission_id in role.permission_ids:
            permission = db.query(Permission).filter(Permission.id == permission_id).first()
            if permission:
                role_permission = RolePermission(role_id=db_role.id, permission_id=permission_id)
                db.add(role_permission)

    db.commit()
    db.refresh(db_role)

    return db_role


@roles_router.get("", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:read")),
):
    """List all roles."""
    roles = db.query(Role).order_by(Role.name).all()
    return roles


@roles_router.get("/{role_id}", response_model=RoleDetailResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:read")),
):
    """Get a specific role with permissions."""
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Get permissions
    permissions = (
        db.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role_id)
        .all()
    )

    return {
        **role.__dict__,
        "permissions": permissions,
    }


@roles_router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:update")),
):
    """Update a role."""
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Cannot update system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system roles",
        )

    # Update role
    update_data = role_update.model_dump(exclude_unset=True, exclude={"permission_ids"})
    for field, value in update_data.items():
        setattr(role, field, value)

    # Update permissions if provided
    if role_update.permission_ids is not None:
        # Remove existing permissions
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

        # Add new permissions
        for permission_id in role_update.permission_ids:
            permission = db.query(Permission).filter(Permission.id == permission_id).first()
            if permission:
                role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
                db.add(role_permission)

    role.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(role)

    return role


@roles_router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:delete")),
):
    """Delete a role."""
    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    # Cannot delete system roles
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles",
        )

    db.delete(role)
    db.commit()


# ================== PERMISSION ENDPOINTS ==================

@permissions_router.get("", response_model=List[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:read")),
):
    """List all permissions."""
    permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()
    return permissions


@permissions_router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("role:read")),
):
    """Get a specific permission."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    return permission
