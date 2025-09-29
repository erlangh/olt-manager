"""
Pydantic models for authentication.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    permissions: Optional[list[str]] = None


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    role: str


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase, one lowercase, and one digit
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['admin', 'operator', 'viewer']
        if v.lower() not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and len(v.strip()) > 0:
            # Basic phone validation - remove spaces and check if it's numeric
            phone_clean = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not phone_clean.isdigit() or len(phone_clean) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = ['admin', 'operator', 'viewer']
            if v.lower() not in valid_roles:
                raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
            return v.lower()
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and len(v.strip()) > 0:
            phone_clean = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not phone_clean.isdigit() or len(phone_clean) < 10:
                raise ValueError('Phone number must be at least 10 digits')
        return v


class PasswordChange(BaseModel):
    """Password change model."""
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('New password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v
    
    @validator('confirm_password')
    def validate_confirm_password(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Password confirmation does not match')
        return v


class PasswordReset(BaseModel):
    """Password reset model."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model."""
    token: str
    new_password: str
    confirm_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('New password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v
    
    @validator('confirm_password')
    def validate_confirm_password(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Password confirmation does not match')
        return v


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response model."""
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class UserStats(BaseModel):
    """User statistics model."""
    total_users: int
    active_users: int
    inactive_users: int
    users_by_role: dict[str, int]
    recent_logins: int  # Users logged in within last 24 hours
    
    
class SessionInfo(BaseModel):
    """Session information model."""
    user_id: int
    username: str
    role: str
    login_time: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True