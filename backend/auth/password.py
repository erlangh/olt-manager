"""
Password handling utilities.
"""

import logging
from typing import Optional
from passlib.context import CryptContext
from passlib.exc import InvalidHashError

logger = logging.getLogger(__name__)


class PasswordHandler:
    """Password hashing and verification handler."""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Higher rounds for better security
        )
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Error hashing password: {str(e)}")
            raise ValueError("Failed to hash password")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except InvalidHashError:
            logger.warning("Invalid password hash format")
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def needs_update(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated."""
        try:
            return self.pwd_context.needs_update(hashed_password)
        except Exception as e:
            logger.error(f"Error checking if password needs update: {str(e)}")
            return False
    
    def generate_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        import secrets
        import string
        
        if length < 8:
            length = 8
        
        # Ensure password has at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Start with one character from each category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest with random characters from all categories
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def validate_password_strength(self, password: str) -> dict:
        """Validate password strength and return detailed feedback."""
        result = {
            "is_valid": True,
            "score": 0,
            "feedback": [],
            "requirements_met": {
                "length": False,
                "uppercase": False,
                "lowercase": False,
                "digit": False,
                "special": False
            }
        }
        
        # Check length
        if len(password) >= 8:
            result["requirements_met"]["length"] = True
            result["score"] += 20
        else:
            result["is_valid"] = False
            result["feedback"].append("Password must be at least 8 characters long")
        
        # Check for uppercase
        if any(c.isupper() for c in password):
            result["requirements_met"]["uppercase"] = True
            result["score"] += 20
        else:
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one uppercase letter")
        
        # Check for lowercase
        if any(c.islower() for c in password):
            result["requirements_met"]["lowercase"] = True
            result["score"] += 20
        else:
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one lowercase letter")
        
        # Check for digit
        if any(c.isdigit() for c in password):
            result["requirements_met"]["digit"] = True
            result["score"] += 20
        else:
            result["is_valid"] = False
            result["feedback"].append("Password must contain at least one digit")
        
        # Check for special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if any(c in special_chars for c in password):
            result["requirements_met"]["special"] = True
            result["score"] += 20
            result["feedback"].append("Great! Password contains special characters")
        else:
            result["feedback"].append("Consider adding special characters for stronger security")
        
        # Additional strength checks
        if len(password) >= 12:
            result["score"] += 10
            result["feedback"].append("Good password length")
        
        # Check for common patterns
        common_patterns = ["123", "abc", "password", "admin", "user"]
        if any(pattern in password.lower() for pattern in common_patterns):
            result["score"] -= 20
            result["feedback"].append("Avoid common patterns in passwords")
        
        # Determine strength level
        if result["score"] >= 90:
            result["strength"] = "Very Strong"
        elif result["score"] >= 70:
            result["strength"] = "Strong"
        elif result["score"] >= 50:
            result["strength"] = "Medium"
        elif result["score"] >= 30:
            result["strength"] = "Weak"
        else:
            result["strength"] = "Very Weak"
        
        return result


# Global password handler instance
_password_handler: Optional[PasswordHandler] = None


def get_password_handler() -> PasswordHandler:
    """Get the global password handler instance."""
    global _password_handler
    if _password_handler is None:
        _password_handler = PasswordHandler()
    return _password_handler


def hash_password(password: str) -> str:
    """Hash a password using the global password handler."""
    return get_password_handler().hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using the global password handler."""
    return get_password_handler().verify_password(plain_password, hashed_password)


def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    return get_password_handler().generate_password(length)


def validate_password_strength(password: str) -> dict:
    """Validate password strength."""
    return get_password_handler().validate_password_strength(password)