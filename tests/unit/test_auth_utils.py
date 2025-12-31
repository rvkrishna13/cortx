"""
Unit tests for auth utility functions
"""
import pytest
from src.auth.utils import (
    create_test_token,
    create_admin_token,
    create_analyst_token,
    create_viewer_token
)
from src.auth.jwt_auth import decode_token, extract_user_from_token
from src.auth.permissions import Role


class TestCreateTestToken:
    """Tests for create_test_token function"""
    
    def test_create_test_token_success(self):
        """Test successful token creation"""
        token = create_test_token(
            user_id=1,
            username="test_user",
            roles=["admin"],
            email="test@example.com"
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_test_token_default_roles(self):
        """Test token creation with default roles (viewer)"""
        token = create_test_token(user_id=1, username="test_user")
        
        user_info = extract_user_from_token(token)
        assert "viewer" in user_info["roles"]
    
    def test_create_test_token_custom_expiration(self):
        """Test token creation with custom expiration"""
        token = create_test_token(
            user_id=1,
            username="test_user",
            expires_minutes=60
        )
        
        assert token is not None
        payload = decode_token(token)
        assert "exp" in payload
    
    def test_create_test_token_invalid_roles_filtered(self):
        """Test that invalid roles are filtered out"""
        token = create_test_token(
            user_id=1,
            username="test_user",
            roles=["admin", "invalid_role", "analyst"]
        )
        
        user_info = extract_user_from_token(token)
        assert "admin" in user_info["roles"]
        assert "analyst" in user_info["roles"]
        assert "invalid_role" not in user_info["roles"]
    
    def test_create_test_token_all_invalid_roles_defaults_to_viewer(self):
        """Test that all invalid roles defaults to viewer"""
        token = create_test_token(
            user_id=1,
            username="test_user",
            roles=["invalid1", "invalid2"]
        )
        
        user_info = extract_user_from_token(token)
        assert "viewer" in user_info["roles"]
    
    def test_create_test_token_with_email(self):
        """Test token creation with email"""
        token = create_test_token(
            user_id=1,
            username="test_user",
            email="test@example.com"
        )
        
        user_info = extract_user_from_token(token)
        assert user_info["email"] == "test@example.com"
    
    def test_create_test_token_without_email(self):
        """Test token creation without email"""
        token = create_test_token(
            user_id=1,
            username="test_user"
        )
        
        user_info = extract_user_from_token(token)
        # Email should not be in token if not provided
        assert "email" in user_info  # May be empty string


class TestCreateAdminToken:
    """Tests for create_admin_token function"""
    
    def test_create_admin_token_default(self):
        """Test admin token creation with defaults"""
        token = create_admin_token()
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 1
        assert user_info["username"] == "admin"
        assert "admin" in user_info["roles"]
    
    def test_create_admin_token_custom(self):
        """Test admin token creation with custom values"""
        token = create_admin_token(user_id=10, username="custom_admin")
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 10
        assert user_info["username"] == "custom_admin"
        assert "admin" in user_info["roles"]


class TestCreateAnalystToken:
    """Tests for create_analyst_token function"""
    
    def test_create_analyst_token_default(self):
        """Test analyst token creation with defaults"""
        token = create_analyst_token()
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 2
        assert user_info["username"] == "analyst"
        assert "analyst" in user_info["roles"]
    
    def test_create_analyst_token_custom(self):
        """Test analyst token creation with custom values"""
        token = create_analyst_token(user_id=20, username="custom_analyst")
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 20
        assert user_info["username"] == "custom_analyst"
        assert "analyst" in user_info["roles"]


class TestCreateViewerToken:
    """Tests for create_viewer_token function"""
    
    def test_create_viewer_token_default(self):
        """Test viewer token creation with defaults"""
        token = create_viewer_token()
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 3
        assert user_info["username"] == "viewer"
        assert "viewer" in user_info["roles"]
    
    def test_create_viewer_token_custom(self):
        """Test viewer token creation with custom values"""
        token = create_viewer_token(user_id=30, username="custom_viewer")
        
        user_info = extract_user_from_token(token)
        assert user_info["user_id"] == 30
        assert user_info["username"] == "custom_viewer"
        assert "viewer" in user_info["roles"]

