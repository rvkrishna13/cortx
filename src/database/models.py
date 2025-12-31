"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime
from src.database.connection import Base


class Transaction(Base):
    """Transactions table"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No foreign key - users table not maintained
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    category = Column(String(100), nullable=True)
    risk_score = Column(Float, nullable=True)


class Portfolio(Base):
    """Portfolios table"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # No foreign key - users table not maintained
    assets = Column(JSON, nullable=True)  # Store assets as JSON
    total_value = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MarketData(Base):
    """Market data table"""
    __tablename__ = "market_data"
    
    symbol = Column(String(20), primary_key=True, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

