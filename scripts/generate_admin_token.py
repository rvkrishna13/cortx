#!/usr/bin/env python3
"""
Generate an admin JWT token for local development
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth.utils import create_admin_token

def main():
    """Generate and print admin token"""
    token = create_admin_token(user_id=1, username="admin")
    print("=" * 80)
    print("🔐 ADMIN JWT TOKEN (for local development)")
    print("=" * 80)
    print(token)
    print("=" * 80)
    print("\n💡 Use this token in API requests:")
    print(f"   Authorization: Bearer {token}")
    print("\n📝 Example curl commands:")
    print(f'   curl -H "Authorization: Bearer {token}" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -X POST http://localhost:8000/api/v1/reasoning \\')
    print('     -d \'{"query": "Get market summary for AAPL", "include_thinking": true}\'')
    print("\n   # Or test MCP endpoint:")
    print(f'   curl -H "Authorization: Bearer {token}" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -X POST http://localhost:8000/api/v1/mcp \\')
    print('     -d \'{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}\'')
    print("=" * 80)
    return token

if __name__ == "__main__":
    main()
