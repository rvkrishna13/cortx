#!/usr/bin/env python3
"""
Generate a viewer JWT token for testing RBAC
Run this with the server's Python environment
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from src.auth.utils import create_viewer_token
    
    # Create viewer token
    token = create_viewer_token(user_id=5, username="test_viewer")
    print(token)
except ImportError as e:
    print(f"Error: {e}", file=sys.stderr)
    print("Make sure to run this with the server's Python environment that has dependencies installed", file=sys.stderr)
    sys.exit(1)

