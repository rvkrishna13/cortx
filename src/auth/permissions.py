"""
Permission definitions and role-based access control
"""
from enum import Enum
from typing import Set, Dict, List


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Available permissions"""
    # Market data permissions
    READ_MARKET_DATA = "read:market_data"
    
    # Transaction permissions
    READ_TRANSACTIONS = "read:transactions"
    READ_USER_TRANSACTIONS = "read:user_transactions"
    
    # Portfolio permissions
    READ_PORTFOLIOS = "read:portfolios"
    READ_USER_PORTFOLIOS = "read:user_portfolios"
    
    # Risk analysis permissions
    READ_RISK_METRICS = "read:risk_metrics"
    
    # Admin permissions
    READ_ALL_DATA = "read:all_data"
    WRITE_ALL_DATA = "write:all_data"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_MARKET_DATA,
    },
    Role.ANALYST: {
        Permission.READ_MARKET_DATA,
        Permission.READ_USER_TRANSACTIONS,
        Permission.READ_USER_PORTFOLIOS,
        Permission.READ_RISK_METRICS,
    },
    Role.ADMIN: {
        Permission.READ_MARKET_DATA,
        Permission.READ_TRANSACTIONS,
        Permission.READ_USER_TRANSACTIONS,
        Permission.READ_PORTFOLIOS,
        Permission.READ_USER_PORTFOLIOS,
        Permission.READ_RISK_METRICS,
        Permission.READ_ALL_DATA,
        Permission.WRITE_ALL_DATA,
    },
}


def get_permissions_for_role(role: Role) -> Set[Permission]:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission"""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permissions(*required_permissions: Permission):
    """Check if role has all required permissions"""
    def check(user_role: Role) -> bool:
        user_perms = get_permissions_for_role(user_role)
        return all(perm in user_perms for perm in required_permissions)
    return check

