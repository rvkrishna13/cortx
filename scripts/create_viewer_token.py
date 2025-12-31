#!/usr/bin/env python3
"""
Quick script to create a viewer JWT token for testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import jwt
from src.config.settings import settings

# Create viewer token
data = {
    "user_id": 5,
    "username": "test_viewer",
    "roles": ["viewer"],
    "exp": datetime.utcnow() + timedelta(minutes=30),
    "iat": datetime.utcnow()
}

token = jwt.encode(
    data,
    settings.JWT_SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM
)

print(token)

