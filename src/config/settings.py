"""
Configuration settings
"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    APP_NAME: str = "Financial MCP Server"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Database settings - PostgreSQL
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/financial_mcp"
    DB_ECHO: bool = False  # Set to True to log SQL queries
    
    # API Keys (if needed)
    CLAUDE_API_KEY: Optional[str] = None
    
    # JWT Settings
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Development/Testing Settings
    ALLOW_UNAUTHENTICATED_ACCESS: bool = False  # Set to True for development/testing
    DEFAULT_UNAUTHENTICATED_ROLE: str = "admin"  # Default role for unauthenticated access
    
    # Logging Settings
    LOG_FILE: Optional[str] = None  # Path to log file (e.g., "logs/app.log"). If None, logs only go to stdout.
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

