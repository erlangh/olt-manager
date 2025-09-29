"""
User model for authentication and authorization.
"""

from sqlalchemy import Column, String, Boolean, Enum, Text
from sqlalchemy.orm import relationship
import enum

from .base import Base


class UserRole(str, enum.Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Basic user information
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Role-based access control
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    
    # Additional information
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(String(255), nullable=True)
    
    # Last login tracking
    last_login = Column(String(255), nullable=True)
    login_count = Column(String(10), default="0", nullable=False)
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_operator(self) -> bool:
        """Check if user has operator role or higher."""
        return self.role in [UserRole.ADMIN, UserRole.OPERATOR]
    
    @property
    def can_read(self) -> bool:
        """Check if user can read data."""
        return self.is_active
    
    @property
    def can_write(self) -> bool:
        """Check if user can write/modify data."""
        return self.is_active and self.role in [UserRole.ADMIN, UserRole.OPERATOR]
    
    @property
    def can_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.is_active and self.role == UserRole.ADMIN