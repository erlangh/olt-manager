"""
FastAPI dependencies for authentication and authorization.
"""

import logging
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from .jwt_handler import verify_token
from .models import TokenData

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify the token
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            logger.warning("Invalid token provided")
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.username == token_data.username).first()
        if user is None:
            logger.warning(f"User not found: {token_data.username}")
            raise credentials_exception
        
        logger.debug(f"Authenticated user: {user.username}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (must be active)."""
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: List[str]):
    """Dependency factory for role-based access control."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"User {current_user.username} with role {current_user.role} "
                f"attempted to access resource requiring roles: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role."""
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.username} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_operator_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require operator or admin role."""
    if not (current_user.is_operator or current_user.is_admin):
        logger.warning(
            f"User {current_user.username} with role {current_user.role} "
            f"attempted operator/admin access"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required"
        )
    return current_user


def optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None."""
    if not credentials:
        return None
    
    try:
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            return None
        
        user = db.query(User).filter(User.username == token_data.username).first()
        if user and user.is_active:
            return user
        return None
        
    except Exception as e:
        logger.debug(f"Optional user authentication failed: {str(e)}")
        return None


class PermissionChecker:
    """Permission-based access control."""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Check if user has required permissions."""
        # Admin users have all permissions
        if current_user.is_admin:
            return current_user
        
        # Check role-based permissions
        user_permissions = self._get_user_permissions(current_user)
        
        missing_permissions = set(self.required_permissions) - set(user_permissions)
        if missing_permissions:
            logger.warning(
                f"User {current_user.username} missing permissions: {missing_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return current_user
    
    def _get_user_permissions(self, user: User) -> List[str]:
        """Get user permissions based on role."""
        role_permissions = {
            "admin": [
                "read:all", "write:all", "delete:all",
                "manage:users", "manage:olts", "manage:onts",
                "manage:configs", "manage:backups", "view:reports",
                "manage:alarms", "manage:monitoring"
            ],
            "operator": [
                "read:olts", "write:olts", "read:onts", "write:onts",
                "read:configs", "write:configs", "read:backups", "write:backups",
                "view:reports", "read:alarms", "write:alarms", "read:monitoring"
            ],
            "viewer": [
                "read:olts", "read:onts", "read:configs", "read:backups",
                "view:reports", "read:alarms", "read:monitoring"
            ]
        }
        
        return role_permissions.get(user.role, [])


def require_permissions(permissions: List[str]):
    """Dependency factory for permission-based access control."""
    return PermissionChecker(permissions)


class RateLimiter:
    """Simple rate limiting for API endpoints."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis or similar
    
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Check rate limit for user."""
        import time
        
        now = time.time()
        user_key = f"rate_limit:{current_user.id}"
        
        # Clean old requests
        if user_key in self.requests:
            self.requests[user_key] = [
                req_time for req_time in self.requests[user_key]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[user_key] = []
        
        # Check if limit exceeded
        if len(self.requests[user_key]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user: {current_user.username}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Add current request
        self.requests[user_key].append(now)
        
        return current_user


def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Dependency factory for rate limiting."""
    return RateLimiter(max_requests, window_seconds)


async def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get token data without database lookup."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        return token_data
        
    except Exception as e:
        logger.error(f"Error getting token data: {str(e)}")
        raise credentials_exception


def create_user_context(user: User) -> dict:
    """Create user context for logging and auditing."""
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser
    }