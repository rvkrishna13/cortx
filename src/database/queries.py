"""
Database query functions for transactions, portfolios, and market data
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.database.models import Transaction, Portfolio, MarketData
from src.utils.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    NotFoundError,
    ValidationError
)


# ============================================================================
# TRANSACTION QUERIES
# ============================================================================

def get_transactions_with_filters(
    db: Session,
    user_id: Optional[int] = None,
    category: Optional[str] = None,
    currency: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    min_risk_score: Optional[float] = None,
    max_risk_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Transaction]:
    """Get transactions with various filters"""
    try:
        # Validate inputs
        if skip < 0:
            raise ValidationError("skip must be non-negative", "skip")
        if limit < 0 or limit > 1000:
            raise ValidationError("limit must be between 0 and 1000", "limit")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise ValidationError("min_amount cannot be greater than max_amount", "amount_range")
        if min_risk_score is not None and max_risk_score is not None and min_risk_score > max_risk_score:
            raise ValidationError("min_risk_score cannot be greater than max_risk_score", "risk_score_range")
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValidationError("start_date cannot be greater than end_date", "date_range")
        
        query = db.query(Transaction)
        
        if user_id is not None:
            query = query.filter(Transaction.user_id == user_id)
        if category is not None:
            query = query.filter(Transaction.category == category)
        if currency is not None:
            query = query.filter(Transaction.currency == currency)
        if start_date is not None:
            query = query.filter(Transaction.timestamp >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.timestamp <= end_date)
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        if min_risk_score is not None:
            query = query.filter(Transaction.risk_score >= min_risk_score)
        if max_risk_score is not None:
            query = query.filter(Transaction.risk_score <= max_risk_score)
        
        return query.order_by(desc(Transaction.timestamp)).offset(skip).limit(limit).all()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query transactions: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying transactions: {str(e)}", e) from e


def get_transaction_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
    """Get a single transaction by ID"""
    try:
        if transaction_id <= 0:
            raise ValidationError("transaction_id must be positive", "transaction_id")
        
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query transaction: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying transaction: {str(e)}", e) from e


def get_user_transaction_count(db: Session, user_id: int) -> int:
    """Get total count of transactions for a user"""
    try:
        if user_id <= 0:
            raise ValidationError("user_id must be positive", "user_id")
        
        return db.query(Transaction).filter(Transaction.user_id == user_id).count()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to count transactions: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error counting transactions: {str(e)}", e) from e


def get_transactions_by_user_and_period(
    db: Session,
    user_id: int,
    start_date: datetime,
    end_date: datetime,
    limit: int = 1000,
    offset: int = 0
) -> List[Transaction]:
    """Get transactions for a user within a specific time period"""
    try:
        if user_id <= 0:
            raise ValidationError("user_id must be positive", "user_id")
        if start_date > end_date:
            raise ValidationError("start_date cannot be greater than end_date", "date_range")
        if limit < 0 or limit > 1000:
            raise ValidationError("limit must be between 0 and 1000", "limit")
        if offset < 0:
            raise ValidationError("offset must be non-negative", "offset")
        
        return db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.timestamp >= start_date,
                Transaction.timestamp <= end_date
            )
        ).order_by(desc(Transaction.timestamp)).limit(limit).offset(offset).all()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query transactions by period: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying transactions: {str(e)}", e) from e


def get_transaction_risk_distribution(
    db: Session,
    user_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get risk score distribution of transactions"""
    try:
        if user_id is not None and user_id <= 0:
            raise ValidationError("user_id must be positive", "user_id")
        
        query = db.query(
            func.avg(Transaction.risk_score).label('avg_risk'),
            func.min(Transaction.risk_score).label('min_risk'),
            func.max(Transaction.risk_score).label('max_risk'),
            func.count(Transaction.id).label('count')
        )
        
        if user_id is not None:
            query = query.filter(Transaction.user_id == user_id)
        
        result = query.first()
        
        if not result:
            return [{
                'avg_risk': 0.0,
                'min_risk': 0.0,
                'max_risk': 0.0,
                'count': 0
            }]
        
        return [{
            'avg_risk': float(result.avg_risk) if result.avg_risk else 0.0,
            'min_risk': float(result.min_risk) if result.min_risk else 0.0,
            'max_risk': float(result.max_risk) if result.max_risk else 0.0,
            'count': result.count
        }]
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to get risk distribution: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error getting risk distribution: {str(e)}", e) from e


def get_transactions_by_category(
    db: Session,
    user_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Transaction]:
    """Get transactions grouped by category"""
    try:
        if user_id is not None and user_id <= 0:
            raise ValidationError("user_id must be positive", "user_id")
        if limit < 0 or limit > 1000:
            raise ValidationError("limit must be between 0 and 1000", "limit")
        if offset < 0:
            raise ValidationError("offset must be non-negative", "offset")
        
        query = db.query(Transaction)
        
        if user_id is not None:
            query = query.filter(Transaction.user_id == user_id)
        if category is not None:
            query = query.filter(Transaction.category == category)
        
        return query.order_by(desc(Transaction.timestamp)).limit(limit).offset(offset).all()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query transactions by category: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying transactions: {str(e)}", e) from e


# ============================================================================
# PORTFOLIO QUERIES
# ============================================================================

def get_portfolio_by_id(db: Session, portfolio_id: int) -> Optional[Portfolio]:
    """Get a portfolio by ID"""
    try:
        if portfolio_id <= 0:
            raise ValidationError("portfolio_id must be positive", "portfolio_id")
        
        return db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query portfolio: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying portfolio: {str(e)}", e) from e


def get_user_portfolios(db: Session, user_id: int) -> List[Portfolio]:
    """Get all portfolios for a user"""
    try:
        if user_id <= 0:
            raise ValidationError("user_id must be positive", "user_id")
        
        return db.query(Portfolio).filter(
            Portfolio.user_id == user_id
        ).order_by(desc(Portfolio.last_updated)).all()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query user portfolios: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying portfolios: {str(e)}", e) from e


def get_portfolio_transaction_history(
    db: Session,
    portfolio_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[Transaction]:
    """Get transaction history for a portfolio's user"""
    if limit < 0 or limit > 1000:
        raise ValidationError("limit must be between 0 and 1000", "limit")
    if offset < 0:
        raise ValidationError("offset must be non-negative", "offset")
    
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return []
    
    query = db.query(Transaction).filter(Transaction.user_id == portfolio.user_id)
    
    if start_date is not None:
        query = query.filter(Transaction.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.timestamp <= end_date)
    
    return query.order_by(desc(Transaction.timestamp)).limit(limit).offset(offset).all()


def get_portfolio_holdings_current_prices(
    db: Session,
    portfolio_id: int
) -> Dict[str, Any]:
    """Get current prices for all holdings in a portfolio"""
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio or not portfolio.assets:
        return {}
    
    # Extract symbols from portfolio assets (assuming assets is a JSON dict/list)
    symbols = []
    if isinstance(portfolio.assets, dict):
        symbols = list(portfolio.assets.keys())
    elif isinstance(portfolio.assets, list):
        symbols = [item.get('symbol') for item in portfolio.assets if isinstance(item, dict) and 'symbol' in item]
    
    if not symbols:
        return {}
    
    # Get latest prices for each symbol
    latest_prices = {}
    for symbol in symbols:
        latest = get_latest_price_per_symbol(db, symbol)
        if latest:
            latest_prices[symbol] = latest.price
    
    return latest_prices


def get_historical_portfolio_values(
    db: Session,
    portfolio_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get historical portfolio values over time"""
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return []
    
    # This would typically require a separate historical_values table
    # For now, return the current value with timestamp
    return [{
        'portfolio_id': portfolio.id,
        'total_value': portfolio.total_value,
        'timestamp': portfolio.last_updated
    }]


def get_portfolio_assets(db: Session, portfolio_id: int) -> Optional[Dict[str, Any]]:
    """Get assets for a portfolio"""
    portfolio = get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        return None
    
    return portfolio.assets if portfolio.assets else {}


# ============================================================================
# MARKET DATA QUERIES
# ============================================================================

def get_market_data_by_symbols(
    db: Session,
    symbols: List[str],
    limit_per_symbol: Optional[int] = None
) -> List[MarketData]:
    """Get market data for multiple symbols"""
    try:
        if not symbols:
            raise ValidationError("symbols list cannot be empty", "symbols")
        if limit_per_symbol is not None and limit_per_symbol < 0:
            raise ValidationError("limit_per_symbol must be non-negative", "limit_per_symbol")
        
        # Normalize symbols
        symbols = [s.upper().strip() for s in symbols if s and s.strip()]
        if not symbols:
            raise ValidationError("No valid symbols provided", "symbols")
        
        query = db.query(MarketData).filter(MarketData.symbol.in_(symbols))
        
        if limit_per_symbol:
            # This is a simplified version - for true per-symbol limiting, 
            # you'd need window functions or separate queries
            query = query.order_by(desc(MarketData.timestamp)).limit(limit_per_symbol * len(symbols))
        else:
            query = query.order_by(desc(MarketData.timestamp))
        
        return query.all()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query market data: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying market data: {str(e)}", e) from e


def get_latest_price_per_symbol(db: Session, symbol: str) -> Optional[MarketData]:
    """Get the latest price data for a symbol"""
    try:
        if not symbol or not symbol.strip():
            raise ValidationError("symbol cannot be empty", "symbol")
        
        return db.query(MarketData).filter(
            MarketData.symbol == symbol.upper().strip()
        ).order_by(desc(MarketData.timestamp)).first()
    
    except ValidationError:
        raise
    except OperationalError as e:
        raise DatabaseConnectionError("Database connection failed", e) from e
    except SQLAlchemyError as e:
        raise DatabaseQueryError(f"Failed to query market data: {str(e)}", e) from e
    except Exception as e:
        raise DatabaseError(f"Unexpected error querying market data: {str(e)}", e) from e


def get_price_history(
    db: Session,
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[MarketData]:
    """Get price history for a symbol within a date range"""
    query = db.query(MarketData).filter(MarketData.symbol == symbol)
    
    if start_date is not None:
        query = query.filter(MarketData.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(MarketData.timestamp <= end_date)
    
    query = query.order_by(desc(MarketData.timestamp))
    
    if limit is not None:
        query = query.limit(limit)
    
    return query.all()


def get_volume_statistics(
    db: Session,
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get volume statistics for a symbol"""
    query = db.query(
        func.avg(MarketData.volume).label('avg_volume'),
        func.min(MarketData.volume).label('min_volume'),
        func.max(MarketData.volume).label('max_volume'),
        func.sum(MarketData.volume).label('total_volume'),
        func.count(MarketData.symbol).label('count')
    ).filter(MarketData.symbol == symbol)
    
    if start_date is not None:
        query = query.filter(MarketData.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(MarketData.timestamp <= end_date)
    
    result = query.first()
    
    return {
        'symbol': symbol,
        'avg_volume': float(result.avg_volume) if result.avg_volume else 0.0,
        'min_volume': int(result.min_volume) if result.min_volume else 0,
        'max_volume': int(result.max_volume) if result.max_volume else 0,
        'total_volume': int(result.total_volume) if result.total_volume else 0,
        'count': result.count
    }


def get_price_changes(
    db: Session,
    symbol: str,
    period_hours: int = 24
) -> Dict[str, Any]:
    """Get price change over a period"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=period_hours)
    
    latest = get_latest_price_per_symbol(db, symbol)
    if not latest:
        return {'symbol': symbol, 'price_change': 0.0, 'percent_change': 0.0}
    
    historical = db.query(MarketData).filter(
        and_(
            MarketData.symbol == symbol,
            MarketData.timestamp >= start_time,
            MarketData.timestamp < latest.timestamp
        )
    ).order_by(MarketData.timestamp).first()
    
    if not historical:
        return {'symbol': symbol, 'price_change': 0.0, 'percent_change': 0.0}
    
    price_change = latest.price - historical.price
    percent_change = (price_change / historical.price * 100) if historical.price > 0 else 0.0
    
    return {
        'symbol': symbol,
        'current_price': latest.price,
        'previous_price': historical.price,
        'price_change': price_change,
        'percent_change': percent_change,
        'period_hours': period_hours
    }


def get_top_movers(
    db: Session,
    limit: int = 10,
    period_hours: int = 24,
    direction: str = "both"  # "up", "down", or "both"
) -> List[Dict[str, Any]]:
    """Get top movers by price change"""
    # Get all unique symbols
    symbols = db.query(MarketData.symbol).distinct().all()
    symbol_list = [s[0] for s in symbols]
    
    movers = []
    for symbol in symbol_list:
        change_data = get_price_changes(db, symbol, period_hours)
        if change_data.get('percent_change', 0) != 0:
            movers.append(change_data)
    
    # Sort by absolute percent change
    movers.sort(key=lambda x: abs(x.get('percent_change', 0)), reverse=True)
    
    # Filter by direction if needed
    if direction == "up":
        movers = [m for m in movers if m.get('percent_change', 0) > 0]
    elif direction == "down":
        movers = [m for m in movers if m.get('percent_change', 0) < 0]
    
    return movers[:limit]


def get_market_data_in_range(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    symbols: Optional[List[str]] = None,
    limit: int = 1000,
    offset: int = 0
) -> List[MarketData]:
    """Get market data within a date range"""
    if limit < 0 or limit > 1000:
        raise ValidationError("limit must be between 0 and 1000", "limit")
    if offset < 0:
        raise ValidationError("offset must be non-negative", "offset")
    
    query = db.query(MarketData).filter(
        and_(
            MarketData.timestamp >= start_date,
            MarketData.timestamp <= end_date
        )
    )
    
    if symbols:
        query = query.filter(MarketData.symbol.in_(symbols))
    
    return query.order_by(desc(MarketData.timestamp)).limit(limit).offset(offset).all()


def get_latest_market_data(
    db: Session,
    symbols: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> List[MarketData]:
    """Get latest market data for symbols"""
    # Get the most recent timestamp
    latest_timestamp = db.query(func.max(MarketData.timestamp)).scalar()
    
    if not latest_timestamp:
        return []
    
    query = db.query(MarketData).filter(MarketData.timestamp == latest_timestamp)
    
    if symbols:
        query = query.filter(MarketData.symbol.in_(symbols))
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


# ============================================================================
# ANALYTICS HELPER QUERIES
# ============================================================================

def aggregate_by_symbol(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Aggregate market data by symbol"""
    query = db.query(
        MarketData.symbol,
        func.avg(MarketData.price).label('avg_price'),
        func.min(MarketData.price).label('min_price'),
        func.max(MarketData.price).label('max_price'),
        func.avg(MarketData.volume).label('avg_volume'),
        func.count(MarketData.symbol).label('count')
    ).group_by(MarketData.symbol)
    
    if start_date is not None:
        query = query.filter(MarketData.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(MarketData.timestamp <= end_date)
    
    results = query.all()
    
    return [{
        'symbol': r.symbol,
        'avg_price': float(r.avg_price) if r.avg_price else 0.0,
        'min_price': float(r.min_price) if r.min_price else 0.0,
        'max_price': float(r.max_price) if r.max_price else 0.0,
        'avg_volume': float(r.avg_volume) if r.avg_volume else 0.0,
        'count': r.count
    } for r in results]


def aggregate_by_time_period(
    db: Session,
    period: str = "day",  # "hour", "day", "week", "month"
    symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Aggregate market data by time period"""
    # Extract date parts based on period
    if period == "hour":
        date_part = func.date_trunc('hour', MarketData.timestamp)
    elif period == "day":
        date_part = func.date_trunc('day', MarketData.timestamp)
    elif period == "week":
        date_part = func.date_trunc('week', MarketData.timestamp)
    elif period == "month":
        date_part = func.date_trunc('month', MarketData.timestamp)
    else:
        date_part = func.date_trunc('day', MarketData.timestamp)
    
    query = db.query(
        date_part.label('period'),
        func.avg(MarketData.price).label('avg_price'),
        func.min(MarketData.price).label('min_price'),
        func.max(MarketData.price).label('max_price'),
        func.sum(MarketData.volume).label('total_volume'),
        func.count(MarketData.symbol).label('count')
    ).group_by(date_part)
    
    if symbol:
        query = query.filter(MarketData.symbol == symbol)
    if start_date is not None:
        query = query.filter(MarketData.timestamp >= start_date)
    if end_date is not None:
        query = query.filter(MarketData.timestamp <= end_date)
    
    results = query.order_by(date_part).all()
    
    return [{
        'period': r.period,
        'avg_price': float(r.avg_price) if r.avg_price else 0.0,
        'min_price': float(r.min_price) if r.min_price else 0.0,
        'max_price': float(r.max_price) if r.max_price else 0.0,
        'total_volume': int(r.total_volume) if r.total_volume else 0,
        'count': r.count
    } for r in results]

def get_latest_prices_dict(db: Session, symbols: List[str]) -> Dict[str, float]:
    """Get latest price for each symbol as a dict"""
    from src.database.models import MarketData
    
    result = {}
    for symbol in symbols:
        latest = db.query(MarketData).filter(
            MarketData.symbol == symbol
        ).order_by(MarketData.timestamp.desc()).first()
        
        if latest:
            result[symbol] = latest.price
    
    return result