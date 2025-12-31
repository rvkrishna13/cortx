"""
Utility functions for authentication and testing
"""
from datetime import timedelta
from typing import List, Optional
from src.auth.jwt_auth import create_access_token
from src.auth.permissions import Role


def create_test_token(
    user_id: int,
    username: str = "test_user",
    roles: Optional[List[str]] = None,
    email: Optional[str] = None,
    expires_minutes: int = 30
) -> str:
    """
    Create a test JWT token for development/testing
    
    Args:
        user_id: User ID
        username: Username
        roles: List of role names (e.g., ["admin", "analyst"])
        email: User email
        expires_minutes: Token expiration time in minutes
    
    Returns:
        JWT token string
    
    Example:
        # Create admin token
        token = create_test_token(
            user_id=1,
            username="admin_user",
            roles=["admin"]
        )
        
        # Create analyst token
        token = create_test_token(
            user_id=2,
            username="analyst_user",
            roles=["analyst"]
        )
        
        # Create viewer token
        token = create_test_token(
            user_id=3,
            username="viewer_user",
            roles=["viewer"]
        )
    """
    if roles is None:
        roles = ["viewer"]
    
    # Validate roles
    valid_roles = [r.value for r in Role]
    roles = [r for r in roles if r in valid_roles]
    
    if not roles:
        roles = ["viewer"]  # Default to viewer if no valid roles
    
    data = {
        "user_id": user_id,
        "username": username,
        "roles": roles,
    }
    
    if email:
        data["email"] = email
    
    return create_access_token(data, expires_delta=timedelta(minutes=expires_minutes))


def create_admin_token(user_id: int = 1, username: str = "admin") -> str:
    """Create a token with admin role"""
    return create_test_token(user_id=user_id, username=username, roles=["admin"])


def create_analyst_token(user_id: int = 2, username: str = "analyst") -> str:
    """Create a token with analyst role"""
    return create_test_token(user_id=user_id, username=username, roles=["analyst"])


def create_viewer_token(user_id: int = 3, username: str = "viewer") -> str:
    """Create a token with viewer role"""
    return create_test_token(user_id=user_id, username=username, roles=["viewer"])

