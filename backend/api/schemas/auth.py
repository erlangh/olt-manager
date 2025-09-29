"""
Authentication API schemas.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator

from ...models.user import UserRole


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreateRequest(BaseModel):
    """Schema for user creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = Field(UserRole.VIEWER)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=50)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdateRequest(BaseModel):
    """Schema for user update request."""
    email: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = Field(None)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = Field(None)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: str = Field(..., max_length=100)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v


class PasswordResetConfirmRequest(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    phone: Optional[str]
    department: Optional[str]
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """Schema for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    role: str = Field("user", description="User role")
    permissions: Optional[List[str]] = Field(default_factory=list)
    is_active: bool = Field(True, description="Whether the user is active")

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('Username must contain only alphanumeric characters, underscores, and hyphens')
        return v


class UserUpdateRequest(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    items: List[UserResponse]
    total: int
    limit: int
    offset: int


class CurrentUserResponse(UserResponse):
    """Schema for current user response with additional info."""
    permissions: List[str] = Field(default_factory=list)
    session_info: Dict = Field(default_factory=dict)


class UserStatsResponse(BaseModel):
    """Schema for user statistics response."""
    total_users: int
    active_users: int
    inactive_users: int
    users_by_role: Dict[str, int]
    recent_registrations: int
    recent_logins: int