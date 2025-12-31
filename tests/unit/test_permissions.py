"""
Unit tests for permissions module
"""
import pytest
from src.auth.permissions import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_role,
    has_permission,
    require_permissions
)


class TestRoleEnum:
    """Tests for Role enum"""
    
    def test_role_values(self):
        """Test that roles have correct values"""
        assert Role.ADMIN.value == "admin"
        assert Role.ANALYST.value == "analyst"
        assert Role.VIEWER.value == "viewer"


class TestPermissionEnum:
    """Tests for Permission enum"""
    
    def test_permission_values(self):
        """Test that permissions have correct values"""
        assert Permission.READ_MARKET_DATA.value == "read:market_data"
        assert Permission.READ_TRANSACTIONS.value == "read:transactions"
        assert Permission.READ_USER_TRANSACTIONS.value == "read:user_transactions"
        assert Permission.READ_PORTFOLIOS.value == "read:portfolios"
        assert Permission.READ_USER_PORTFOLIOS.value == "read:user_portfolios"
        assert Permission.READ_RISK_METRICS.value == "read:risk_metrics"
        assert Permission.READ_ALL_DATA.value == "read:all_data"
        assert Permission.WRITE_ALL_DATA.value == "write:all_data"


class TestRolePermissions:
    """Tests for role permissions mapping"""
    
    def test_viewer_permissions(self):
        """Test viewer role permissions"""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.READ_MARKET_DATA in viewer_perms
        assert Permission.READ_TRANSACTIONS not in viewer_perms
        assert Permission.READ_ALL_DATA not in viewer_perms
    
    def test_analyst_permissions(self):
        """Test analyst role permissions"""
        analyst_perms = ROLE_PERMISSIONS[Role.ANALYST]
        assert Permission.READ_MARKET_DATA in analyst_perms
        assert Permission.READ_USER_TRANSACTIONS in analyst_perms
        assert Permission.READ_USER_PORTFOLIOS in analyst_perms
        assert Permission.READ_RISK_METRICS in analyst_perms
        assert Permission.READ_ALL_DATA not in analyst_perms
        assert Permission.WRITE_ALL_DATA not in analyst_perms
    
    def test_admin_permissions(self):
        """Test admin role permissions"""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.READ_MARKET_DATA in admin_perms
        assert Permission.READ_TRANSACTIONS in admin_perms
        assert Permission.READ_USER_TRANSACTIONS in admin_perms
        assert Permission.READ_PORTFOLIOS in admin_perms
        assert Permission.READ_USER_PORTFOLIOS in admin_perms
        assert Permission.READ_RISK_METRICS in admin_perms
        assert Permission.READ_ALL_DATA in admin_perms
        assert Permission.WRITE_ALL_DATA in admin_perms


class TestGetPermissionsForRole:
    """Tests for get_permissions_for_role function"""
    
    def test_get_permissions_for_viewer(self):
        """Test getting permissions for viewer role"""
        perms = get_permissions_for_role(Role.VIEWER)
        assert isinstance(perms, set)
        assert Permission.READ_MARKET_DATA in perms
    
    def test_get_permissions_for_analyst(self):
        """Test getting permissions for analyst role"""
        perms = get_permissions_for_role(Role.ANALYST)
        assert isinstance(perms, set)
        assert len(perms) >= 4
    
    def test_get_permissions_for_admin(self):
        """Test getting permissions for admin role"""
        perms = get_permissions_for_role(Role.ADMIN)
        assert isinstance(perms, set)
        assert len(perms) >= 8
    
    def test_get_permissions_for_invalid_role(self):
        """Test getting permissions for invalid role"""
        # Create a mock role that doesn't exist
        class InvalidRole(str):
            pass
        
        perms = get_permissions_for_role(InvalidRole())  # type: ignore
        assert isinstance(perms, set)
        assert len(perms) == 0


class TestHasPermission:
    """Tests for has_permission function"""
    
    def test_viewer_has_market_data_permission(self):
        """Test that viewer has market data permission"""
        assert has_permission(Role.VIEWER, Permission.READ_MARKET_DATA) is True
    
    def test_viewer_does_not_have_transactions_permission(self):
        """Test that viewer does not have transactions permission"""
        assert has_permission(Role.VIEWER, Permission.READ_TRANSACTIONS) is False
    
    def test_analyst_has_user_transactions_permission(self):
        """Test that analyst has user transactions permission"""
        assert has_permission(Role.ANALYST, Permission.READ_USER_TRANSACTIONS) is True
    
    def test_admin_has_all_permissions(self):
        """Test that admin has all permissions"""
        assert has_permission(Role.ADMIN, Permission.READ_MARKET_DATA) is True
        assert has_permission(Role.ADMIN, Permission.READ_TRANSACTIONS) is True
        assert has_permission(Role.ADMIN, Permission.READ_ALL_DATA) is True
        assert has_permission(Role.ADMIN, Permission.WRITE_ALL_DATA) is True
    
    def test_invalid_role_has_no_permissions(self):
        """Test that invalid role has no permissions"""
        class InvalidRole(str):
            pass
        
        assert has_permission(InvalidRole(), Permission.READ_MARKET_DATA) is False  # type: ignore


class TestRequirePermissions:
    """Tests for require_permissions function"""
    
    def test_require_permissions_single_permission(self):
        """Test require_permissions with single permission"""
        check = require_permissions(Permission.READ_MARKET_DATA)
        
        assert check(Role.VIEWER) is True
        assert check(Role.ANALYST) is True
        assert check(Role.ADMIN) is True
    
    def test_require_permissions_multiple_permissions(self):
        """Test require_permissions with multiple permissions"""
        check = require_permissions(
            Permission.READ_MARKET_DATA,
            Permission.READ_USER_TRANSACTIONS
        )
        
        assert check(Role.VIEWER) is False  # Viewer doesn't have READ_USER_TRANSACTIONS
        assert check(Role.ANALYST) is True  # Analyst has both
        assert check(Role.ADMIN) is True  # Admin has both
    
    def test_require_permissions_admin_only(self):
        """Test require_permissions for admin-only permissions"""
        check = require_permissions(Permission.READ_ALL_DATA)
        
        assert check(Role.VIEWER) is False
        assert check(Role.ANALYST) is False
        assert check(Role.ADMIN) is True

