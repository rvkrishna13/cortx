"""
Sample data fixtures for testing
"""
from datetime import datetime, timedelta
from src.database.models import Transaction, Portfolio, MarketData


def create_sample_transaction(user_id=1, amount=100.0, category="Stock Purchase"):
    """Create a sample transaction object"""
    return Transaction(
        user_id=user_id,
        amount=amount,
        currency="USD",
        timestamp=datetime.utcnow(),
        category=category,
        risk_score=0.5
    )


def create_sample_portfolio(user_id=1, total_value=10000.0):
    """Create a sample portfolio object"""
    return Portfolio(
        user_id=user_id,
        assets={"AAPL": {"shares": 100, "price": 175.0, "value": 17500.0}},
        total_value=total_value,
        last_updated=datetime.utcnow()
    )


def create_sample_market_data(symbol="AAPL", price=175.0):
    """Create a sample market data object"""
    return MarketData(
        symbol=symbol,
        price=price,
        volume=1000000,
        timestamp=datetime.utcnow()
    )


def get_sample_transactions_data():
    """Get sample transaction data as dictionaries"""
    return [
        {
            "user_id": 1,
            "amount": 100.0,
            "currency": "USD",
            "category": "Stock Purchase",
            "risk_score": 0.3
        },
        {
            "user_id": 1,
            "amount": 500.0,
            "currency": "USD",
            "category": "Stock Sale",
            "risk_score": 0.5
        },
        {
            "user_id": 2,
            "amount": 1000.0,
            "currency": "EUR",
            "category": "Dividend",
            "risk_score": 0.2
        }
    ]


def get_sample_portfolios_data():
    """Get sample portfolio data as dictionaries"""
    return [
        {
            "user_id": 1,
            "assets": {"AAPL": {"shares": 100, "price": 175.0, "value": 17500.0}},
            "total_value": 17500.0
        },
        {
            "user_id": 1,
            "assets": {
                "GOOGL": {"shares": 50, "price": 140.0, "value": 7000.0},
                "MSFT": {"shares": 30, "price": 380.0, "value": 11400.0}
            },
            "total_value": 18400.0
        }
    ]


def get_sample_market_data_list():
    """Get sample market data as list"""
    return [
        {"symbol": "AAPL", "price": 175.0, "volume": 1000000},
        {"symbol": "GOOGL", "price": 140.0, "volume": 2000000},
        {"symbol": "MSFT", "price": 380.0, "volume": 1500000}
    ]

