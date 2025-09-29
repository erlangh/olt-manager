"""
JWT token handling utilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from .models import TokenData

logger = logging.getLogger(__name__)


class JWTHandler:
    """JWT token handler for authentication."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise ValueError("Failed to create access token")
    
    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise ValueError("Failed to create refresh token")
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
                return None
            
            # Extract user information
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            role: str = payload.get("role")
            permissions: list = payload.get("permissions", [])
            
            if username is None or user_id is None:
                logger.warning("Token missing required claims")
                return None
            
            token_data = TokenData(
                username=username,
                user_id=user_id,
                role=role,
                permissions=permissions
            )
            
            logger.debug(f"Successfully verified {token_type} token for user: {username}")
            return token_data
            
        except ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except JWTClaimsError as e:
            logger.warning(f"Invalid token claims: {str(e)}")
            return None
        except JWTError as e:
            logger.warning(f"JWT error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            return None
    
    def decode_token_without_verification(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging/inspection)."""
        try:
            return jwt.get_unverified_claims(token)
        except Exception as e:
            logger.error(f"Error decoding token: {str(e)}")
            return None
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiry time."""
        try:
            payload = jwt.get_unverified_claims(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.utcfromtimestamp(exp_timestamp)
            return None
        except Exception as e:
            logger.error(f"Error getting token expiry: {str(e)}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired."""
        try:
            expiry = self.get_token_expiry(token)
            if expiry:
                return datetime.utcnow() > expiry
            return True
        except Exception:
            return True
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token."""
        token_data = self.verify_token(refresh_token, token_type="refresh")
        if not token_data:
            return None
        
        # Create new access token with same data
        access_token_data = {
            "sub": token_data.username,
            "user_id": token_data.user_id,
            "role": token_data.role,
            "permissions": token_data.permissions or []
        }
        
        return self.create_access_token(access_token_data)
    
    def create_password_reset_token(self, email: str) -> str:
        """Create a password reset token."""
        expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        to_encode = {
            "sub": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "password_reset"
        }
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created password reset token for email: {email}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating password reset token: {str(e)}")
            raise ValueError("Failed to create password reset token")
    
    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return email."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "password_reset":
                logger.warning("Invalid token type for password reset")
                return None
            
            email = payload.get("sub")
            if not email:
                logger.warning("Password reset token missing email")
                return None
            
            logger.debug(f"Successfully verified password reset token for email: {email}")
            return email
            
        except ExpiredSignatureError:
            logger.warning("Password reset token has expired")
            return None
        except JWTError as e:
            logger.warning(f"Invalid password reset token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying password reset token: {str(e)}")
            return None
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """Get comprehensive token information."""
        info = {
            "valid": False,
            "expired": True,
            "type": None,
            "username": None,
            "user_id": None,
            "role": None,
            "issued_at": None,
            "expires_at": None,
            "time_to_expiry": None
        }
        
        try:
            # Get unverified claims first
            payload = jwt.get_unverified_claims(token)
            
            info.update({
                "type": payload.get("type"),
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "role": payload.get("role"),
                "issued_at": datetime.utcfromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.utcfromtimestamp(payload.get("exp", 0))
            })
            
            # Check if expired
            if info["expires_at"]:
                now = datetime.utcnow()
                info["expired"] = now > info["expires_at"]
                if not info["expired"]:
                    info["time_to_expiry"] = info["expires_at"] - now
            
            # Try to verify token
            token_data = self.verify_token(token, token_type=payload.get("type", "access"))
            info["valid"] = token_data is not None
            
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
        
        return info


# Global JWT handler instance
_jwt_handler: Optional[JWTHandler] = None


def get_jwt_handler() -> JWTHandler:
    """Get the global JWT handler instance."""
    global _jwt_handler
    if _jwt_handler is None:
        # These should be loaded from environment variables
        import os
        secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
        algorithm = os.getenv("ALGORITHM", "HS256")
        access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        _jwt_handler = JWTHandler(
            secret_key=secret_key,
            algorithm=algorithm,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days
        )
    return _jwt_handler


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token using the global JWT handler."""
    return get_jwt_handler().create_access_token(data, expires_delta)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create refresh token using the global JWT handler."""
    return get_jwt_handler().create_refresh_token(data, expires_delta)


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify token using the global JWT handler."""
    return get_jwt_handler().verify_token(token, token_type)