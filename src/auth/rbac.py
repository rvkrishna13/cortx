"""
Role-Based Access Control (RBAC) decorators for MCP tools
"""
from functools import wraps
from typing import Callable, Any, List, Optional, Dict
from src.auth.permissions import Role, Permission, has_permission, get_permissions_for_role
from src.auth.jwt_auth import extract_user_from_token, validate_token
from src.config.settings import settings
from src.utils.exceptions import ValidationError, NotFoundError


def get_user_from_context(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract user information from context (token, headers, etc.)
    
    Args:
        context: Context dictionary containing token or user info
    
    Returns:
        User information dictionary
    
    Raises:
        ValidationError: If token is invalid or missing (unless unauthenticated access is allowed)
    """
    # Check if unauthenticated access is allowed (either explicitly or in DEBUG mode)
    allow_unauth = settings.ALLOW_UNAUTHENTICATED_ACCESS or settings.DEBUG
    
    # If unauthenticated access is allowed and no context provided, return default user
    if allow_unauth and not context:
        default_role = settings.DEFAULT_UNAUTHENTICATED_ROLE
        return {
            "user_id": 0,  # Anonymous user
            "username": "anonymous",
            "email": "",
            "roles": [default_role]
        }
    
    if not context:
        raise ValidationError("Authentication context is required", "auth")
    
    # Try to get token from context
    token = context.get("token") or context.get("authorization")
    
    # If unauthenticated access is allowed and no token, return default user
    if allow_unauth and not token:
        default_role = settings.DEFAULT_UNAUTHENTICATED_ROLE
        return {
            "user_id": 0,  # Anonymous user
            "username": "anonymous",
            "email": "",
            "roles": [default_role]
        }
    
    if not token:
        raise ValidationError("Authentication token is required", "auth")
    
    # Remove "Bearer " prefix if present
    if isinstance(token, str) and token.startswith("Bearer "):
        token = token[7:]
    
    return extract_user_from_token(token)


def require_role(*allowed_roles: Role):
    """
    Decorator to require specific roles for MCP tool access
    
    Usage:
        @require_role(Role.ADMIN, Role.ANALYST)
        def query_transactions(db, arguments, context=None):
            current_user = kwargs.get("current_user")
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get context from kwargs (passed as separate parameter)
            # Allow None context - get_user_from_context will handle unauthenticated access
            context = kwargs.get("context") or kwargs.get("auth_context")
            
            # Extract user from token (handles unauthenticated access if DEBUG=True)
            try:
                user_info = get_user_from_context(context)
            except ValidationError as e:
                # If a token was provided but is invalid, always reject (don't fall back)
                has_token = context and (context.get("token") or context.get("authorization"))
                if has_token:
                    raise ValidationError(
                        f"Invalid or expired authentication token: {e.message}",
                        "auth"
                    )
                # If unauthenticated access is not allowed, re-raise
                if not (settings.ALLOW_UNAUTHENTICATED_ACCESS or settings.DEBUG):
                    raise
                # Otherwise, use default anonymous user (only if no token was provided)
                default_role = settings.DEFAULT_UNAUTHENTICATED_ROLE
                user_info = {
                    "user_id": 0,
                    "username": "anonymous",
                    "email": "",
                    "roles": [default_role]
                }
            
            user_roles = [Role(role) for role in user_info.get("roles", []) if role in [r.value for r in Role]]
            
            if not user_roles:
                raise ValidationError("User has no valid roles", "auth")
            
            # Check if user has at least one of the required roles
            has_access = any(role in allowed_roles for role in user_roles)
            
            if not has_access:
                allowed_role_names = [role.value for role in allowed_roles]
                user_role_names = [role.value for role in user_roles]
                raise ValidationError(
                    f"Access denied. Required roles: {allowed_role_names}, User roles: {user_role_names}",
                    "auth"
                )
            
            # Add user info to kwargs for use in the function
            kwargs["current_user"] = user_info
            kwargs["user_roles"] = user_roles
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(*required_permissions: Permission):
    """
    Decorator to require specific permissions for MCP tool access
    
    Usage:
        @require_permission(Permission.READ_TRANSACTIONS)
        def query_transactions(db, arguments, context=None):
            current_user = kwargs.get("current_user")
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get context from kwargs (passed as separate parameter)
            # Allow None context - get_user_from_context will handle unauthenticated access
            context = kwargs.get("context") or kwargs.get("auth_context")
            
            # Extract user from token (handles unauthenticated access if DEBUG=True)
            try:
                user_info = get_user_from_context(context)
            except ValidationError as e:
                # If a token was provided but is invalid, always reject (don't fall back)
                has_token = context and (context.get("token") or context.get("authorization"))
                if has_token:
                    raise ValidationError(
                        f"Invalid or expired authentication token: {e.message}",
                        "auth"
                    )
                # If unauthenticated access is not allowed, re-raise
                if not (settings.ALLOW_UNAUTHENTICATED_ACCESS or settings.DEBUG):
                    raise
                # Otherwise, use default anonymous user (only if no token was provided)
                default_role = settings.DEFAULT_UNAUTHENTICATED_ROLE
                user_info = {
                    "user_id": 0,
                    "username": "anonymous",
                    "email": "",
                    "roles": [default_role]
                }
            
            user_roles = [Role(role) for role in user_info.get("roles", []) if role in [r.value for r in Role]]
            
            if not user_roles:
                raise ValidationError("User has no valid roles", "auth")
            
            # Check if user has all required permissions
            user_permissions = set()
            for role in user_roles:
                user_permissions.update(get_permissions_for_role(role))
            
            missing_permissions = [perm for perm in required_permissions if perm not in user_permissions]
            
            if missing_permissions:
                raise ValidationError(
                    f"Missing required permissions: {[p.value for p in missing_permissions]}",
                    "auth"
                )
            
            # Add user info to kwargs
            kwargs["current_user"] = user_info
            kwargs["user_roles"] = user_roles
            kwargs["user_permissions"] = user_permissions
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_user_access(user_id: int, current_user: Dict[str, Any], user_roles: List[Role]) -> bool:
    """
    Check if current user can access data for a specific user_id
    
    Rules:
    - Admin: Can access all users
    - Analyst: Can only access assigned users (user_id matches current_user["user_id"])
    - Viewer: Cannot access user-specific data
    
    Args:
        user_id: Target user ID to check access for
        current_user: Current user information
        user_roles: List of current user's roles
    
    Returns:
        True if access is allowed, False otherwise
    """
    current_user_id = current_user.get("user_id")
    
    # Admin has full access
    if Role.ADMIN in user_roles:
        return True
    
    # Analyst can only access their own data or assigned users
    if Role.ANALYST in user_roles:
        # For now, analyst can only access their own data
        # Later, you can add an "assigned_users" field to check
        return user_id == current_user_id
    
    # Viewer cannot access user-specific data
    return False


def enforce_user_access(user_id: Optional[int], current_user: Dict[str, Any], user_roles: List[Role]):
    """
    Enforce user access rules and raise exception if access denied
    
    Args:
        user_id: Target user ID to check access for
        current_user: Current user information
        user_roles: List of current user's roles
    
    Raises:
        ValidationError: If access is denied
    """
    if user_id is None:
        return  # No user_id specified, skip check
    
    if not check_user_access(user_id, current_user, user_roles):
        current_user_id = current_user.get("user_id")
        raise ValidationError(
            f"Access denied. User {current_user_id} cannot access data for user {user_id}",
            "auth"
        )

