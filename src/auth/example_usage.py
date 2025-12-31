"""
Example usage of JWT authentication and RBAC decorators for MCP tools

This file demonstrates how to use the authentication and authorization system
with MCP tools. It's for reference only and not meant to be executed directly.
"""
from src.auth.jwt_auth import create_access_token, extract_user_from_token
from src.auth.rbac import require_role, require_permission, enforce_user_access
from src.auth.permissions import Role, Permission
from src.auth.utils import create_test_token, create_admin_token, create_analyst_token, create_viewer_token
from src.mcp.tools import call_tool


# ============================================================================
# Example 1: Creating JWT Tokens
# ============================================================================

def example_create_tokens():
    """Example: Create JWT tokens for different roles"""
    
    # Method 1: Using utility functions
    admin_token = create_admin_token(user_id=1, username="admin_user")
    analyst_token = create_analyst_token(user_id=2, username="analyst_user")
    viewer_token = create_viewer_token(user_id=3, username="viewer_user")
    
    # Method 2: Using create_test_token directly
    custom_token = create_test_token(
        user_id=5,
        username="custom_user",
        roles=["analyst", "viewer"],  # Multiple roles
        email="user@example.com"
    )
    
    # Method 3: Using create_access_token directly
    token_data = {
        "user_id": 10,
        "username": "direct_user",
        "roles": ["admin"],
        "email": "admin@example.com"
    }
    direct_token = create_access_token(token_data)
    
    print(f"Admin token: {admin_token[:50]}...")
    print(f"Analyst token: {analyst_token[:50]}...")
    print(f"Viewer token: {viewer_token[:50]}...")


# ============================================================================
# Example 2: Using MCP Tools with Authentication Context
# ============================================================================

def example_call_tool_with_auth():
    """Example: Call MCP tools with authentication context"""
    
    # Create a token for an analyst user
    token = create_analyst_token(user_id=2, username="analyst_user")
    
    # Create authentication context
    context = {
        "token": token,
        # or "authorization": f"Bearer {token}"
    }
    
    # Call query_transactions tool
    # Analyst can only query their own transactions (user_id=2)
    # Note: context is passed separately, not mixed with arguments
    result = call_tool(
        name="query_transactions",
        arguments={
            "user_id": 2,  # Analyst can only access their own data
            "limit": 10
        },
        context=context  # Authentication context passed separately
    )
    
    print(f"Query result: {result}")
    
    # Call get_market_summary tool (viewer, analyst, admin can all access)
    result = call_tool(
        name="get_market_summary",
        arguments={
            "symbols": ["AAPL", "GOOGL"]
        },
        context=context  # Clean separation: arguments vs context
    )
    
    print(f"Market summary: {result}")
    
    # Try to access another user's data (will fail for analyst)
    try:
        result = call_tool(
            name="query_transactions",
            arguments={
                "user_id": 5,  # Different user - analyst cannot access
                "limit": 10
            },
            context=context
        )
    except Exception as e:
        print(f"Access denied (expected): {e}")


# ============================================================================
# Example 3: Admin Access (Full Access)
# ============================================================================

def example_admin_access():
    """Example: Admin user has full access to all data"""
    
    admin_token = create_admin_token(user_id=1, username="admin")
    context = {"token": admin_token}
    
    # Admin can query any user's transactions
    # Clean API: arguments contain only business logic params, context is separate
    result = call_tool(
        name="query_transactions",
        arguments={
            "user_id": 5,  # Admin can access any user
            "limit": 10
        },
        context=context  # Auth context passed separately
    )
    
    print(f"Admin query result: {result}")


# ============================================================================
# Example 4: Viewer Access (Read-Only Market Data)
# ============================================================================

def example_viewer_access():
    """Example: Viewer can only access public market data"""
    
    viewer_token = create_viewer_token(user_id=3, username="viewer")
    context = {"token": viewer_token}
    
    # Viewer can access market data
    result = call_tool(
        name="get_market_summary",
        arguments={
            "symbols": ["AAPL", "GOOGL", "MSFT"]
        },
        context=context
    )
    
    print(f"Viewer market data: {result}")
    
    # Viewer cannot access transactions (will fail)
    try:
        result = call_tool(
            name="query_transactions",
            arguments={"user_id": 3},
            context=context
        )
    except Exception as e:
        print(f"Access denied (expected): {e}")


# ============================================================================
# Example 5: Extracting User Info from Token
# ============================================================================

def example_extract_user_info():
    """Example: Extract user information from a token"""
    
    token = create_analyst_token(user_id=2, username="analyst_user")
    
    # Extract user info
    user_info = extract_user_from_token(token)
    
    print(f"User ID: {user_info['user_id']}")
    print(f"Username: {user_info['username']}")
    print(f"Roles: {user_info['roles']}")
    print(f"Email: {user_info.get('email', 'N/A')}")


# ============================================================================
# Example 6: Using Decorators in Custom Functions
# ============================================================================

def example_custom_decorated_function():
    """Example: Using RBAC decorators in your own functions"""
    
    @require_role(Role.ADMIN, Role.ANALYST)
    def analyze_portfolio(portfolio_id: int, context: dict = None, **kwargs):
        """Function that requires admin or analyst role"""
        current_user = kwargs.get("current_user", {})
        user_roles = kwargs.get("user_roles", [])
        
        print(f"Analyzing portfolio {portfolio_id} for user {current_user.get('user_id')}")
        print(f"User roles: {[r.value for r in user_roles]}")
        
        # Enforce user access if needed
        # enforce_user_access(target_user_id, current_user, user_roles)
        
        return {"status": "success", "portfolio_id": portfolio_id}
    
    # Call with admin token
    admin_context = {"token": create_admin_token()}
    result = analyze_portfolio(portfolio_id=1, context=admin_context)
    print(f"Result: {result}")
    
    # Call with viewer token (will fail)
    try:
        viewer_context = {"token": create_viewer_token()}
        result = analyze_portfolio(portfolio_id=1, context=viewer_context)
    except Exception as e:
        print(f"Access denied (expected): {e}")


if __name__ == "__main__":
    print("=" * 80)
    print("JWT Authentication and RBAC Examples")
    print("=" * 80)
    
    print("\n1. Creating tokens...")
    example_create_tokens()
    
    print("\n2. Extracting user info...")
    example_extract_user_info()
    
    print("\n3. Using decorators in custom functions...")
    example_custom_decorated_function()
    
    print("\n" + "=" * 80)
    print("Note: To test MCP tool calls, ensure the database is set up and seeded.")
    print("=" * 80)

