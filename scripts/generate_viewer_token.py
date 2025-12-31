#!/usr/bin/env python3
"""
Generate a JWT token with viewer role for testing RBAC
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.utils import create_viewer_token

if __name__ == "__main__":
    token = create_viewer_token()
    
    print("=" * 60)
    print("🔑 VIEWER JWT TOKEN GENERATED")
    print("=" * 60)
    print()
    print("Token:")
    print(token)
    print()
    print("=" * 60)
    print("📋 Usage Examples:")
    print("=" * 60)
    print()
    print("curl -X POST http://localhost:8000/api/v1/reasoning \\")
    print("  -H 'Authorization: Bearer " + token + "' \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"query\": \"Get market summary for AAPL\"}'")
    print()
    print("=" * 60)
    print("⚠️  Viewer Role Permissions:")
    print("=" * 60)
    print("✅ Can access: Market data (public)")
    print("❌ Cannot access: Transactions, Risk metrics, User data")
    print()
    print("💡 Save this token for your demo video!")
    print("=" * 60)
