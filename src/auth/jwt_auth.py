"""
JWT token validation and authentication utilities
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from src.config.settings import settings
from src.utils.exceptions import ValidationError


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token (typically user_id, username, roles)
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        ValidationError: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise ValidationError(f"Invalid token: {str(e)}", "token")
    except Exception as e:
        raise ValidationError(f"Token validation error: {str(e)}", "token")


def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate a JWT token and return the payload
    
    Args:
        token: JWT token string (with or without "Bearer " prefix)
    
    Returns:
        Decoded token payload with user information
    
    Raises:
        ValidationError: If token is invalid
    """
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    if not token:
        raise ValidationError("Token is required", "token")
    
    payload = decode_token(token)
    
    # Validate required fields
    if "user_id" not in payload and "sub" not in payload:
        raise ValidationError("Token missing user identifier", "token")
    
    return payload


def extract_user_from_token(token: str) -> Dict[str, Any]:
    """
    Extract user information from JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Dictionary with user information:
        - user_id: User ID
        - username: Username
        - roles: List of user roles
        - email: User email (if present)
    """
    payload = validate_token(token)
    
    user_id = payload.get("user_id") or payload.get("sub")
    username = payload.get("username") or payload.get("preferred_username", "")
    email = payload.get("email", "")
    roles = payload.get("roles", [])
    
    # Ensure roles is a list
    if isinstance(roles, str):
        roles = [roles]
    elif not isinstance(roles, list):
        roles = []
    
    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "roles": roles
    }

