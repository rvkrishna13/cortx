"""
FastAPI dependencies
"""
from src.database.connection import database

# Re-export database singleton for convenience
# Use: database.get_session() for database sessions
__all__ = ["database"]

