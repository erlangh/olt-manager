"""
Authentication package for OLT Manager.
"""

from .jwt_handler import JWTHandler, create_access_token, verify_token
from .password import PasswordHandler, hash_password, verify_password
from .dependencies import get_current_user, get_current_active_user, require_role
from .models import TokenData, Token, UserCreate, UserUpdate, UserResponse

__all__ = [
    "JWTHandler",
    "create_access_token",
    "verify_token",
    "PasswordHandler", 
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "TokenData",
    "Token",
    "UserCreate",
    "UserUpdate", 
    "UserResponse"
]