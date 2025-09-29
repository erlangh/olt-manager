"""
User management API endpoints.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..database.connection import get_db
from ..models.user import User
from ..auth.dependencies import get_current_active_user, require_permissions
from ..auth.password import hash_password, generate_password
from .schemas.auth import (
    UserCreateRequest, UserUpdateRequest, UserResponse, 
    UserListResponse, UserStatsResponse
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    search: Optional[str] = Query(None, description="Search by username, email, or full name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:read"]))
):
    """Get list of users with filtering and pagination."""
    
    query = db.query(User)
    
    # Apply search filter
    if search:
        search_filter = or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Apply role filter
    if role:
        query = query.filter(User.role == role)
    
    # Apply active status filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    # Convert to response models
    user_responses = []
    for user in users:
        user_responses.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login
        ))
    
    return UserListResponse(
        items=user_responses,
        total=total,
        limit=limit,
        offset=skip
    )


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:write"]))
):
    """Create a new user."""
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate password if not provided
    password = user_data.password or generate_password()
    password_hash = hash_password(password)
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
        phone_number=user_data.phone_number,
        role=user_data.role,
        permissions=user_data.permissions,
        is_active=user_data.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        phone_number=new_user.phone_number,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
        last_login=new_user.last_login
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:read"]))
):
    """Get a specific user by ID."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:write"]))
):
    """Update a user."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    # Update fields
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    
    if user_update.role is not None:
        user.role = user_update.role
    
    if user_update.permissions is not None:
        user.permissions = user_update.permissions
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:delete"]))
):
    """Delete a user."""
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:write"]))
):
    """Activate a user account."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "User activated successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:write"]))
):
    """Deactivate a user account."""
    
    # Prevent self-deactivation
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:write"]))
):
    """Reset a user's password to a generated one."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate new password
    new_password = generate_password()
    password_hash = hash_password(new_password)
    
    # Update password
    user.password_hash = password_hash
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # In a real application, you would send this password via email
    # For now, we'll return it (remove in production)
    return {
        "message": "Password reset successfully",
        "new_password": new_password  # Remove this in production
    }


@router.get("/stats/overview", response_model=UserStatsResponse)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["users:read"]))
):
    """Get user statistics overview."""
    
    # Get total counts
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users
    
    # Get counts by role
    role_stats = db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    
    role_counts = {role: count for role, count in role_stats}
    
    # Get recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.query(User).filter(
        User.created_at >= thirty_days_ago
    ).count()
    
    # Get recent logins (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_logins = db.query(User).filter(
        and_(
            User.last_login >= twenty_four_hours_ago,
            User.last_login.isnot(None)
        )
    ).count()
    
    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        users_by_role=role_counts,
        recent_registrations=recent_registrations,
        recent_logins=recent_logins
    )