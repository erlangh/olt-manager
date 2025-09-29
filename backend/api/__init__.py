"""
API package for OLT Manager.
"""

from .olt import router as olt_router
from .ont import router as ont_router
from .auth import router as auth_router
from .monitoring import router as monitoring_router
from .users import router as users_router

__all__ = [
    "olt_router",
    "ont_router", 
    "auth_router",
    "monitoring_router",
    "users_router"
]