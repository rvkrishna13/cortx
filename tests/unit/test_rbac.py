"""
Unit tests for RBAC enforcement
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.auth.rbac import (
    require_role,
    require_permission,
    get_user_from_context,
    check_user_access,
    enforce_user_access
)
from src.auth.permissions import Role, Permission
from src.utils.exceptions import ValidationError
from src.config.settings import settings


class TestGetUserFromContext:
    """Tests for get_user_from_context function"""
    
    @patch('src.auth.rbac.extract_user_from_token')
    def test_get_user_from_context_with_valid_token(self, mock_extract):
        """Test getting user from valid token"""
        mock_extract.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "valid_token"}
        user_info = get_user_from_context(context)
        
        assert user_info["user_id"] == 1
        assert user_info["username"] == "admin"
        assert "admin" in user_info["roles"]
        mock_extract.assert_called_once_with("valid_token")
    
    @patch('src.auth.rbac.extract_user_from_token')
    def test_get_user_from_context_with_bearer_token(self, mock_extract):
        """Test getting user from Bearer token"""
        mock_extract.return_value = {
            "user_id": 2,
            "username": "analyst",
            "roles": ["analyst"]
        }
        
        context = {"token": "Bearer valid_token"}
        user_info = get_user_from_context(context)
        
        assert user_info["user_id"] == 2
        mock_extract.assert_called_once_with("valid_token")
    
    @patch('src.auth.rbac.extract_user_from_token')
    def test_get_user_from_context_invalid_token(self, mock_extract):
        """Test getting user from invalid token"""
        mock_extract.side_effect = ValidationError("Invalid token", "token")
        
        context = {"token": "invalid_token"}
        
        with pytest.raises(ValidationError) as exc_info:
            get_user_from_context(context)
        
        assert "Invalid token" in str(exc_info.value)
    
    @patch('src.auth.rbac.settings')
    def test_get_user_from_context_no_token_unauth_allowed(self, mock_settings):
        """Test getting user when no token but unauthenticated access allowed"""
        mock_settings.ALLOW_UNAUTHENTICATED_ACCESS = True
        mock_settings.DEBUG = False
        mock_settings.DEFAULT_UNAUTHENTICATED_ROLE = "admin"
        
        user_info = get_user_from_context(None)
        
        assert user_info["user_id"] == 0
        assert user_info["username"] == "anonymous"
        assert "admin" in user_info["roles"]
    
    @patch('src.auth.rbac.settings')
    def test_get_user_from_context_no_token_unauth_not_allowed(self, mock_settings):
        """Test getting user when no token and unauthenticated access not allowed"""
        mock_settings.ALLOW_UNAUTHENTICATED_ACCESS = False
        mock_settings.DEBUG = False
        
        with pytest.raises(ValidationError) as exc_info:
            get_user_from_context(None)
        
        assert "Authentication context is required" in str(exc_info.value)


class TestRequireRoleDecorator:
    """Tests for require_role decorator"""
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_role_admin_success(self, mock_get_user):
        """Test admin role can access admin-only function"""
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        @require_role(Role.ADMIN)
        def admin_function(context=None, **kwargs):
            return "success"
        
        context = {"token": "admin_token"}
        result = admin_function(context=context)
        
        assert result == "success"
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_role_analyst_success(self, mock_get_user):
        """Test analyst role can access analyst function"""
        mock_get_user.return_value = {
            "user_id": 2,
            "username": "analyst",
            "roles": ["analyst"]
        }
        
        @require_role(Role.ANALYST, Role.ADMIN)
        def analyst_function(context=None, **kwargs):
            return "success"
        
        context = {"token": "analyst_token"}
        result = analyst_function(context=context)
        
        assert result == "success"
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_role_viewer_denied(self, mock_get_user):
        """Test viewer role cannot access admin function"""
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        @require_role(Role.ADMIN)
        def admin_function(context=None, **kwargs):
            return "success"
        
        context = {"token": "viewer_token"}
        
        with pytest.raises(ValidationError) as exc_info:
            admin_function(context=context)
        
        assert "Access denied" in str(exc_info.value)
        assert "admin" in str(exc_info.value).lower()
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_role_invalid_token(self, mock_get_user):
        """Test require_role with invalid token"""
        mock_get_user.side_effect = ValidationError("Invalid token", "token")
        
        @require_role(Role.ADMIN)
        def admin_function(context=None, **kwargs):
            return "success"
        
        context = {"token": "invalid_token"}
        
        with pytest.raises(ValidationError) as exc_info:
            admin_function(context=context)
        
        assert "Invalid or expired authentication token" in str(exc_info.value)


class TestRequirePermissionDecorator:
    """Tests for require_permission decorator"""
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_permission_admin_success(self, mock_get_user):
        """Test admin has all permissions"""
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        @require_permission(Permission.READ_TRANSACTIONS)
        def read_transactions(context=None, **kwargs):
            return "success"
        
        context = {"token": "admin_token"}
        result = read_transactions(context=context)
        
        assert result == "success"
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_permission_viewer_denied(self, mock_get_user):
        """Test viewer cannot access transactions"""
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        @require_permission(Permission.READ_TRANSACTIONS)
        def read_transactions(context=None, **kwargs):
            return "success"
        
        context = {"token": "viewer_token"}
        
        with pytest.raises(ValidationError) as exc_info:
            read_transactions(context=context)
        
        assert "Missing required permissions" in str(exc_info.value)
        assert "read:transactions" in str(exc_info.value)
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_permission_viewer_can_access_market_data(self, mock_get_user):
        """Test viewer can access market data"""
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        @require_permission(Permission.READ_MARKET_DATA)
        def read_market_data(context=None, **kwargs):
            return "success"
        
        context = {"token": "viewer_token"}
        result = read_market_data(context=context)
        
        assert result == "success"
    
    @patch('src.auth.rbac.get_user_from_context')
    def test_require_permission_analyst_can_access_user_transactions(self, mock_get_user):
        """Test analyst can access user transactions"""
        mock_get_user.return_value = {
            "user_id": 2,
            "username": "analyst",
            "roles": ["analyst"]
        }
        
        @require_permission(Permission.READ_USER_TRANSACTIONS)
        def read_user_transactions(context=None, **kwargs):
            return "success"
        
        context = {"token": "analyst_token"}
        result = read_user_transactions(context=context)
        
        assert result == "success"


class TestCheckUserAccess:
    """Tests for check_user_access function"""
    
    def test_check_user_access_admin_all_access(self):
        """Test admin can access all users"""
        current_user = {"user_id": 1}
        user_roles = [Role.ADMIN]
        
        result = check_user_access(user_id=999, current_user=current_user, user_roles=user_roles)
        
        assert result is True
    
    def test_check_user_access_analyst_own_data(self):
        """Test analyst can access their own data"""
        current_user = {"user_id": 2}
        user_roles = [Role.ANALYST]
        
        result = check_user_access(user_id=2, current_user=current_user, user_roles=user_roles)
        
        assert result is True
    
    def test_check_user_access_analyst_other_user_denied(self):
        """Test analyst cannot access other users' data"""
        current_user = {"user_id": 2}
        user_roles = [Role.ANALYST]
        
        result = check_user_access(user_id=3, current_user=current_user, user_roles=user_roles)
        
        assert result is False
    
    def test_check_user_access_viewer_denied(self):
        """Test viewer cannot access user-specific data"""
        current_user = {"user_id": 5}
        user_roles = [Role.VIEWER]
        
        result = check_user_access(user_id=5, current_user=current_user, user_roles=user_roles)
        
        assert result is False


class TestEnforceUserAccess:
    """Tests for enforce_user_access function"""
    
    def test_enforce_user_access_admin_all_access(self):
        """Test admin can access all users"""
        current_user = {"user_id": 1}
        user_roles = [Role.ADMIN]
        
        # Should not raise exception
        enforce_user_access(user_id=999, current_user=current_user, user_roles=user_roles)
    
    def test_enforce_user_access_analyst_own_data(self):
        """Test analyst can access their own data"""
        current_user = {"user_id": 2}
        user_roles = [Role.ANALYST]
        
        # Should not raise exception
        enforce_user_access(user_id=2, current_user=current_user, user_roles=user_roles)
    
    def test_enforce_user_access_analyst_other_user_denied(self):
        """Test analyst cannot access other users' data"""
        current_user = {"user_id": 2}
        user_roles = [Role.ANALYST]
        
        with pytest.raises(ValidationError) as exc_info:
            enforce_user_access(user_id=3, current_user=current_user, user_roles=user_roles)
        
        assert "Access denied" in str(exc_info.value)
        assert "user 2" in str(exc_info.value).lower()
        assert "user 3" in str(exc_info.value).lower()
    
    def test_enforce_user_access_none_skips_check(self):
        """Test enforce_user_access with None user_id skips check"""
        current_user = {"user_id": 2}
        user_roles = [Role.ANALYST]
        
        # Should not raise exception
        enforce_user_access(user_id=None, current_user=current_user, user_roles=user_roles)

