"""
Pytest configuration and fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from src.database.connection import Base
from src.database.models import Transaction, Portfolio, MarketData


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_transactions(test_db: Session):
    """Create sample transactions for testing"""
    transactions = []
    for i in range(10):
        transaction = Transaction(
            user_id=1,
            amount=100.0 * (i + 1),
            currency="USD",
            timestamp=datetime.utcnow() - timedelta(days=i),
            category="Stock Purchase" if i % 2 == 0 else "Stock Sale",
            risk_score=0.3 + (i * 0.05)
        )
        transactions.append(transaction)
        test_db.add(transaction)
    
    # Add transactions for different users
    for i in range(5):
        transaction = Transaction(
            user_id=2,
            amount=50.0 * (i + 1),
            currency="EUR",
            timestamp=datetime.utcnow() - timedelta(days=i),
            category="Dividend",
            risk_score=0.2
        )
        transactions.append(transaction)
        test_db.add(transaction)
    
    test_db.commit()
    return transactions


@pytest.fixture
def sample_portfolios(test_db: Session):
    """Create sample portfolios for testing"""
    portfolios = []
    
    # Portfolio 1
    portfolio1 = Portfolio(
        user_id=1,
        assets={"AAPL": {"shares": 100, "price": 175.0, "value": 17500.0}},
        total_value=17500.0,
        last_updated=datetime.utcnow()
    )
    portfolios.append(portfolio1)
    test_db.add(portfolio1)
    
    # Portfolio 2
    portfolio2 = Portfolio(
        user_id=1,
        assets={
            "GOOGL": {"shares": 50, "price": 140.0, "value": 7000.0},
            "MSFT": {"shares": 30, "price": 380.0, "value": 11400.0}
        },
        total_value=18400.0,
        last_updated=datetime.utcnow() - timedelta(days=1)
    )
    portfolios.append(portfolio2)
    test_db.add(portfolio2)
    
    # Portfolio 3 for user 2
    portfolio3 = Portfolio(
        user_id=2,
        assets={"TSLA": {"shares": 20, "price": 250.0, "value": 5000.0}},
        total_value=5000.0,
        last_updated=datetime.utcnow() - timedelta(days=2)
    )
    portfolios.append(portfolio3)
    test_db.add(portfolio3)
    
    test_db.commit()
    return portfolios


@pytest.fixture
def sample_market_data(test_db: Session):
    """Create sample market data for testing"""
    market_data = []
    symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "META"]
    
    for symbol in symbols:
        data = MarketData(
            symbol=symbol,
            price=100.0 + len(symbol) * 10,
            volume=1000000,
            timestamp=datetime.utcnow()
        )
        market_data.append(data)
        test_db.add(data)
    
    test_db.commit()
    return market_data


@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock database session for testing MCP tools"""
    from unittest.mock import MagicMock
    mock_session = MagicMock()
    return mock_session

