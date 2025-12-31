# Security Model

Documentation of the security model, including authentication, authorization, and RBAC implementation.

## Overview

The Financial MCP Server implements JWT-based authentication with Role-Based Access Control (RBAC) to secure access to MCP tools and data.

## Authentication

### JWT Token Authentication

All API endpoints require JWT token authentication via the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

### Token Structure

JWT tokens contain:
- `user_id`: Unique user identifier
- `username`: User's username
- `roles`: Array of user roles (e.g., ["admin"], ["analyst"], ["viewer"])
- `exp`: Token expiration timestamp
- `iat`: Token issuance timestamp

### Token Generation

```python
from src.auth.utils import create_admin_token, create_analyst_token, create_viewer_token

# Admin token (full access)
admin_token = create_admin_token(user_id=1, username="admin")

# Analyst token (limited access)
analyst_token = create_analyst_token(user_id=2, username="analyst")

# Viewer token (read-only market data)
viewer_token = create_viewer_token(user_id=5, username="viewer")
```

### Configuration

```env
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Authorization: Role-Based Access Control (RBAC)

### Roles

Three roles are defined with different permission levels:

#### 1. Admin
- **Full access** to all tools and data
- Can query all transactions (any user_id)
- Can access all portfolios
- Can perform all operations
- Can access all market data

#### 2. Analyst
- **Limited access** to assigned user data
- Can query transactions for their own user_id only
- Can access their own portfolios
- Can perform risk analysis
- Can access market data
- **Cannot** access other users' transactions/portfolios

#### 3. Viewer
- **Read-only** access to public market data
- Can access market data only
- **Cannot** access transactions
- **Cannot** access portfolios
- **Cannot** perform risk analysis

### Permissions

Granular permissions are defined:

- `READ_MARKET_DATA`: Access to market data (all roles)
- `READ_TRANSACTIONS`: Access to all transactions (admin only)
- `READ_USER_TRANSACTIONS`: Access to user-specific transactions (analyst, admin)
- `READ_PORTFOLIOS`: Access to all portfolios (admin only)
- `READ_USER_PORTFOLIOS`: Access to user-specific portfolios (analyst, admin)
- `READ_RISK_METRICS`: Access to risk analysis (analyst, admin)
- `READ_ALL_DATA`: Read all data (admin only)
- `WRITE_ALL_DATA`: Write all data (admin only)

### Tool Access Matrix

| Tool | Admin | Analyst | Viewer |
|------|-------|---------|--------|
| `query_transactions` | ✅ All users | ✅ Own user only | ❌ |
| `analyze_risk_metrics` | ✅ All portfolios | ✅ Own portfolios | ❌ |
| `get_market_summary` | ✅ | ✅ | ✅ |

## Implementation

### RBAC Decorators

MCP tools use decorators to enforce permissions:

```python
from src.auth.rbac import require_permission
from src.auth.permissions import Permission

@require_permission(Permission.READ_TRANSACTIONS, Permission.READ_USER_TRANSACTIONS)
def _query_transactions(db, arguments, context=None):
    # Tool implementation
    pass
```

### User Context Extraction

The system extracts user information from JWT tokens:

```python
from src.auth.rbac import get_user_from_context

context = {"token": "Bearer <jwt-token>"}
user = get_user_from_context(context)
# Returns: {"user_id": 1, "username": "admin", "roles": ["admin"]}
```

### Access Control Enforcement

The RBAC system enforces:
1. **Token Validation**: Validates JWT token signature and expiration
2. **Role Checking**: Verifies user has required role
3. **Permission Checking**: Verifies user has required permission
4. **User Data Access**: Enforces user-specific data access rules

## Error Handling

### Authentication Errors

- **401 Unauthorized**: Missing or invalid token
- **401 Unauthorized**: Expired token
- **401 Unauthorized**: Invalid token signature

### Authorization Errors

- **403 Forbidden**: Insufficient permissions
- **403 Forbidden**: Access denied to user-specific data
- **ValidationError**: Missing required permissions

## Security Best Practices

### Token Security

1. **Strong Secret Key**: Use a strong, random JWT_SECRET_KEY
2. **Token Expiration**: Set appropriate expiration times
3. **HTTPS Only**: Use HTTPS in production to protect tokens
4. **Token Storage**: Store tokens securely on client side

### Access Control

1. **Principle of Least Privilege**: Grant minimum required permissions
2. **User Data Isolation**: Enforce user-specific data access
3. **Regular Audits**: Review and audit access permissions
4. **Token Rotation**: Implement token rotation for long-lived sessions

### API Security

1. **Rate Limiting**: Implement rate limiting on endpoints
2. **Input Validation**: Validate all input parameters
3. **SQL Injection Prevention**: Use parameterized queries
4. **CORS Configuration**: Configure CORS appropriately

## Example Usage

### Admin Access

```python
from src.mcp.tools import call_tool

context = {"token": admin_token}
result = call_tool(
    name="query_transactions",
    arguments={"user_id": 1, "limit": 10},
    context=context
)
# ✅ Success - admin can access any user's transactions
```

### Analyst Access

```python
context = {"token": analyst_token}
result = call_tool(
    name="query_transactions",
    arguments={"user_id": 2},  # Analyst's own user_id
    context=context
)
# ✅ Success - analyst can access own transactions

result = call_tool(
    name="query_transactions",
    arguments={"user_id": 1},  # Different user_id
    context=context
)
# ❌ Error - analyst cannot access other users' transactions
```

### Viewer Access

```python
context = {"token": viewer_token}
result = call_tool(
    name="get_market_summary",
    arguments={},
    context=context
)
# ✅ Success - viewer can access market data

result = call_tool(
    name="query_transactions",
    arguments={"user_id": 1},
    context=context
)
# ❌ Error - viewer cannot access transactions
```

## Testing

RBAC is tested with unit tests covering:
- Token validation
- Role-based access
- Permission-based access
- User-specific data access
- Error handling

See `tests/unit/test_rbac.py` for comprehensive test coverage.

