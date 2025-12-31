"""
Unit tests for database queries with mocked database responses
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from src.database.queries import (
    get_transactions_with_filters,
    get_transaction_by_id,
    get_user_transaction_count,
    get_transactions_by_user_and_period,
    get_transaction_risk_distribution,
    get_transactions_by_category,
    get_portfolio_by_id,
    get_user_portfolios,
    get_portfolio_transaction_history,
    get_portfolio_assets,
    get_portfolio_holdings_current_prices,
    get_historical_portfolio_values,
    get_market_data_by_symbols,
    get_latest_price_per_symbol,
    get_price_history,
    get_volume_statistics,
    get_price_changes,
    get_top_movers,
    get_latest_market_data,
    aggregate_by_symbol,
    aggregate_by_time_period,
    get_latest_prices_dict,
    get_market_data_in_range
)
from src.utils.exceptions import ValidationError, DatabaseConnectionError, DatabaseQueryError, DatabaseError


class TestTransactionQueriesMocked:
    """Tests for transaction query functions with mocked database"""
    
    def test_get_transactions_with_filters_user_id(self):
        """Test filtering transactions by user_id"""
        mock_db = MagicMock()
        mock_transactions = []
        for i in range(5):
            tx = Mock()
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0 * (i + 1)
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            tx.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_transactions.append(tx)
        
        # Mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, user_id=1)
        
        assert len(result) == 5
        assert all(tx.user_id == 1 for tx in result)
        mock_db.query.assert_called_once()
    
    def test_get_transactions_with_filters_category(self):
        """Test filtering transactions by category"""
        mock_db = MagicMock()
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.category = "Stock Purchase"
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0
            tx.currency = "USD"
            tx.risk_score = 0.5
            tx.timestamp = datetime.utcnow()
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, category="Stock Purchase")
        
        assert len(result) == 3
        assert all(tx.category == "Stock Purchase" for tx in result)
    
    def test_get_transactions_with_filters_amount_range(self):
        """Test filtering transactions by amount range"""
        mock_db = MagicMock()
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.amount = 200.0 + (i * 100)
            tx.user_id = 1
            tx.id = i + 1
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            tx.timestamp = datetime.utcnow()
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, min_amount=200.0, max_amount=500.0)
        
        assert len(result) == 3
        assert all(200.0 <= tx.amount <= 500.0 for tx in result)
    
    def test_get_transactions_with_filters_date_range(self):
        """Test filtering transactions by date range"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=5)
        end_date = datetime.utcnow()
        
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.timestamp = start_date + timedelta(days=i)
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, start_date=start_date, end_date=end_date)
        
        assert len(result) == 3
        assert all(start_date <= tx.timestamp <= end_date for tx in result)
    
    def test_get_transactions_with_filters_validation_error(self):
        """Test validation error for invalid skip"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, skip=-1)
        
        assert "skip must be non-negative" in str(exc_info.value)
    
    def test_get_transactions_with_filters_invalid_limit(self):
        """Test validation error for invalid limit"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, limit=2000)  # > 1000
        
        assert "limit must be between 0 and 1000" in str(exc_info.value)
    
    def test_get_transactions_with_filters_invalid_amount_range(self):
        """Test validation error for invalid amount range"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, min_amount=500.0, max_amount=200.0)
        
        assert "min_amount cannot be greater than max_amount" in str(exc_info.value)
    
    def test_get_transactions_with_filters_database_error(self):
        """Test database error handling"""
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(DatabaseQueryError):
            get_transactions_with_filters(mock_db, user_id=1)
    
    def test_get_transaction_by_id_success(self):
        """Test getting a transaction by ID"""
        mock_db = MagicMock()
        mock_transaction = Mock()
        mock_transaction.id = 1
        mock_transaction.user_id = 1
        mock_transaction.amount = 100.0
        mock_transaction.currency = "USD"
        mock_transaction.category = "Stock Purchase"
        mock_transaction.risk_score = 0.5
        mock_transaction.timestamp = datetime.utcnow()
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_transaction
        mock_db.query.return_value = mock_query
        
        result = get_transaction_by_id(mock_db, 1)
        
        assert result is not None
        assert result.id == 1
        assert result.user_id == 1
    
    def test_get_transaction_by_id_not_found(self):
        """Test getting a non-existent transaction"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = get_transaction_by_id(mock_db, 999)
        
        assert result is None
    
    def test_get_transaction_by_id_invalid_id(self):
        """Test validation error for invalid transaction ID"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transaction_by_id(mock_db, -1)
        
        assert "transaction_id must be positive" in str(exc_info.value)
    
    def test_get_user_transaction_count_success(self):
        """Test counting transactions for a user"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_db.query.return_value = mock_query
        
        result = get_user_transaction_count(mock_db, user_id=1)
        
        assert result == 10
    
    def test_get_user_transaction_count_invalid_user_id(self):
        """Test validation error for invalid user_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_user_transaction_count(mock_db, user_id=0)
        
        assert "user_id must be positive" in str(exc_info.value)
    
    def test_get_transactions_by_user_and_period_success(self):
        """Test getting transactions for a user within a period"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=3)
        end_date = datetime.utcnow()
        
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.user_id = 1
            tx.timestamp = start_date + timedelta(days=i)
            tx.id = i + 1
            tx.amount = 100.0
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        # Make sure all() returns the actual list, not a mock
        mock_query.all = Mock(return_value=mock_transactions)
        mock_db.query.return_value = mock_query
        
        result = get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date)
        
        assert len(result) == 3
        assert all(tx.user_id == 1 for tx in result)
    
    def test_get_transactions_by_user_and_period_invalid_date_range(self):
        """Test validation error for invalid date range"""
        mock_db = MagicMock()
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(days=1)
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date)
        
        assert "start_date cannot be greater than end_date" in str(exc_info.value)
    
    def test_get_transaction_risk_distribution_success(self):
        """Test getting risk distribution"""
        mock_db = MagicMock()
        mock_result = Mock()
        mock_result.avg_risk = 0.5
        mock_result.min_risk = 0.2
        mock_result.max_risk = 0.8
        mock_result.count = 10
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_result
        mock_db.query.return_value = mock_query
        
        result = get_transaction_risk_distribution(mock_db, user_id=1)
        
        assert len(result) == 1
        assert result[0]['avg_risk'] == 0.5
        assert result[0]['min_risk'] == 0.2
        assert result[0]['max_risk'] == 0.8
        assert result[0]['count'] == 10
    
    def test_get_transaction_risk_distribution_no_results(self):
        """Test getting risk distribution with no results"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = get_transaction_risk_distribution(mock_db, user_id=1)
        
        assert len(result) == 1
        assert result[0]['count'] == 0
        assert result[0]['avg_risk'] == 0.0


class TestPortfolioQueriesMocked:
    """Tests for portfolio query functions with mocked database"""
    
    def test_get_portfolio_by_id_success(self):
        """Test getting a portfolio by ID"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        mock_portfolio.user_id = 1
        mock_portfolio.total_value = 10000.0
        mock_portfolio.assets = {"AAPL": {"shares": 100, "price": 175.0}}
        mock_portfolio.last_updated = datetime.utcnow()
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_portfolio
        mock_db.query.return_value = mock_query
        
        result = get_portfolio_by_id(mock_db, 1)
        
        assert result is not None
        assert result.id == 1
        assert result.user_id == 1
    
    def test_get_portfolio_by_id_not_found(self):
        """Test getting a non-existent portfolio"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = get_portfolio_by_id(mock_db, 999)
        
        assert result is None
    
    def test_get_portfolio_by_id_invalid_id(self):
        """Test validation error for invalid portfolio ID"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_portfolio_by_id(mock_db, -1)
        
        assert "portfolio_id must be positive" in str(exc_info.value)
    
    def test_get_user_portfolios_success(self):
        """Test getting all portfolios for a user"""
        mock_db = MagicMock()
        mock_portfolios = []
        for i in range(2):
            p = Mock()
            p.id = i + 1
            p.user_id = 1
            p.total_value = 10000.0 * (i + 1)
            p.assets = {}
            p.last_updated = datetime.utcnow()
            mock_portfolios.append(p)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_portfolios
        mock_db.query.return_value = mock_query
        
        result = get_user_portfolios(mock_db, user_id=1)
        
        assert len(result) == 2
        assert all(p.user_id == 1 for p in result)
    
    def test_get_portfolio_assets_success(self):
        """Test getting portfolio assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = {"AAPL": {"shares": 100, "price": 175.0}}
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_portfolio
        mock_db.query.return_value = mock_query
        
        result = get_portfolio_assets(mock_db, portfolio_id=1)
        
        assert result is not None
        assert "AAPL" in result
        assert result["AAPL"]["shares"] == 100
    
    def test_get_portfolio_assets_not_found(self):
        """Test getting assets for non-existent portfolio"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = get_portfolio_assets(mock_db, portfolio_id=999)
        
        assert result is None


class TestMarketDataQueriesMocked:
    """Tests for market data query functions with mocked database"""
    
    def test_get_market_data_by_symbols_success(self):
        """Test getting market data for multiple symbols"""
        mock_db = MagicMock()
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        mock_data = []
        for symbol in symbols:
            md = Mock()
            md.symbol = symbol
            md.price = 100.0 + len(symbol) * 10
            md.volume = 1000000
            md.timestamp = datetime.utcnow()
            mock_data.append(md)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_data
        mock_db.query.return_value = mock_query
        
        result = get_market_data_by_symbols(mock_db, symbols)
        
        assert len(result) == 3
        assert all(d.symbol in symbols for d in result)
    
    def test_get_latest_price_per_symbol_success(self):
        """Test getting latest price for a symbol"""
        mock_db = MagicMock()
        mock_data = Mock()
        mock_data.symbol = "AAPL"
        mock_data.price = 175.5
        mock_data.volume = 1000000
        mock_data.timestamp = datetime.utcnow()
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_data
        mock_db.query.return_value = mock_query
        
        result = get_latest_price_per_symbol(mock_db, "AAPL")
        
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.price == 175.5
    
    def test_get_latest_price_per_symbol_not_found(self):
        """Test getting price for non-existent symbol"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        
        result = get_latest_price_per_symbol(mock_db, "INVALID")
        
        assert result is None
    
    def test_get_price_history_success(self):
        """Test getting price history"""
        mock_db = MagicMock()
        mock_history = []
        for i in range(5):
            md = Mock()
            md.symbol = "AAPL"
            md.price = 175.0 + (i * 0.5)
            md.volume = 1000000
            md.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_history.append(md)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_history
        mock_db.query.return_value = mock_query
        
        result = get_price_history(mock_db, "AAPL")
        
        assert len(result) == 5
        assert all(h.symbol == "AAPL" for h in result)
    
    def test_get_volume_statistics_success(self):
        """Test getting volume statistics"""
        mock_db = MagicMock()
        mock_result = Mock()
        mock_result.symbol = "AAPL"
        mock_result.avg_volume = 1000000.0
        mock_result.min_volume = 500000
        mock_result.max_volume = 2000000
        mock_result.total_volume = 5000000
        mock_result.count = 5
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_result
        mock_db.query.return_value = mock_query
        
        result = get_volume_statistics(mock_db, "AAPL")
        
        assert result['symbol'] == "AAPL"
        assert result['avg_volume'] == 1000000.0
        assert result['min_volume'] == 500000
        assert result['max_volume'] == 2000000
        assert result['total_volume'] == 5000000
        assert result['count'] == 5
    
    def test_aggregate_by_symbol_success(self):
        """Test aggregating market data by symbol"""
        mock_db = MagicMock()
        mock_results = [
            Mock(symbol="AAPL", avg_price=175.0, min_price=170.0, max_price=180.0, 
                 avg_volume=1000000.0, count=10),
            Mock(symbol="GOOGL", avg_price=140.0, min_price=135.0, max_price=145.0,
                 avg_volume=2000000.0, count=15)
        ]
        
        mock_query = MagicMock()
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = mock_results
        mock_db.query.return_value = mock_query
        
        result = aggregate_by_symbol(mock_db)
        
        assert len(result) == 2
        assert all('symbol' in r for r in result)
        assert all('avg_price' in r for r in result)
    
    def test_aggregate_by_time_period_success(self):
        """Test aggregating market data by time period"""
        mock_db = MagicMock()
        # Create proper mock objects with all required attributes
        mock_result1 = Mock()
        mock_result1.period = "2024-01-01"
        mock_result1.avg_price = 175.0
        mock_result1.min_price = 170.0
        mock_result1.max_price = 180.0
        mock_result1.total_volume = 1000000
        mock_result1.count = 10
        
        mock_result2 = Mock()
        mock_result2.period = "2024-01-02"
        mock_result2.avg_price = 176.0
        mock_result2.min_price = 171.0
        mock_result2.max_price = 181.0
        mock_result2.total_volume = 1100000
        mock_result2.count = 11
        
        mock_results = [mock_result1, mock_result2]
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_results
        mock_db.query.return_value = mock_query
        
        result = aggregate_by_time_period(mock_db, period="day", symbol="AAPL")
        
        assert len(result) == 2
        assert all('period' in r for r in result)
        assert all('avg_price' in r for r in result)
    
    def test_get_latest_prices_dict_success(self):
        """Test getting latest prices as dictionary"""
        mock_db = MagicMock()
        
        # Create separate mocks for each symbol query
        def mock_query_factory(symbol):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            
            # Return a mock with the price for this symbol
            mock_data = Mock()
            mock_data.symbol = symbol
            mock_data.price = 175.0 if symbol == "AAPL" else 140.0
            mock_query.first.return_value = mock_data
            return mock_query
        
        # Make query() return different mocks for each call
        mock_db.query.side_effect = lambda model: mock_query_factory("AAPL" if model.__name__ == "MarketData" else None)
        
        # Actually, we need to handle multiple calls - one per symbol
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            symbol = ["AAPL", "GOOGL"][call_count[0] - 1] if call_count[0] <= 2 else "AAPL"
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_data = Mock()
            mock_data.symbol = symbol
            mock_data.price = 175.0 if symbol == "AAPL" else 140.0
            mock_query.first.return_value = mock_data
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = get_latest_prices_dict(mock_db, ["AAPL", "GOOGL"])
        
        assert isinstance(result, dict)
        assert result["AAPL"] == 175.0
        assert result["GOOGL"] == 140.0
    
    def test_get_market_data_by_symbols_database_error(self):
        """Test database error handling"""
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(DatabaseQueryError):
            get_market_data_by_symbols(mock_db, ["AAPL"])
    
    def test_get_portfolio_transaction_history_success(self):
        """Test getting portfolio transaction history"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.user_id = 1
        
        mock_portfolio_query = MagicMock()
        mock_portfolio_query.filter.return_value = mock_portfolio_query
        mock_portfolio_query.first.return_value = mock_portfolio
        
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0 * (i + 1)
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            tx.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_transactions.append(tx)
        
        mock_tx_query = MagicMock()
        mock_tx_query.filter.return_value = mock_tx_query
        mock_tx_query.order_by.return_value = mock_tx_query
        mock_tx_query.offset.return_value = mock_tx_query
        mock_tx_query.limit.return_value = mock_tx_query
        mock_tx_query.all = Mock(return_value=mock_transactions)
        
        # Mock db.query to return different queries based on model
        def query_side_effect(model):
            if model.__name__ == "Portfolio":
                return mock_portfolio_query
            else:
                return mock_tx_query
        
        mock_db.query.side_effect = query_side_effect
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        result = get_portfolio_transaction_history(mock_db, portfolio_id=1, start_date=start_date, end_date=end_date)
        
        assert len(result) == 3
        assert all(tx.user_id == 1 for tx in result)



class TestQueryLimits:
    """Tests for query limit and pagination functionality"""
    
    def test_get_transactions_by_user_and_period_with_limit(self):
        """Test that limit parameter works correctly"""
        mock_db = Mock()
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all = Mock(return_value=[])
        
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        result = get_transactions_by_user_and_period(
            mock_db, user_id=1, start_date=start_date, end_date=end_date, limit=50, offset=0
        )
        
        assert result == []
        mock_query.limit.assert_called_once_with(50)
        mock_query.offset.assert_called_once_with(0)
    
    def test_get_transactions_by_user_and_period_invalid_limit(self):
        """Test that invalid limit raises ValidationError"""
        mock_db = Mock()
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        with pytest.raises(ValidationError, match="limit must be between 0 and 1000"):
            get_transactions_by_user_and_period(
                mock_db, user_id=1, start_date=start_date, end_date=end_date, limit=2000
            )
    
    def test_get_transactions_by_user_and_period_negative_offset(self):
        """Test that negative offset raises ValidationError"""
        mock_db = Mock()
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        with pytest.raises(ValidationError, match="offset must be non-negative"):
            get_transactions_by_user_and_period(
                mock_db, user_id=1, start_date=start_date, end_date=end_date, offset=-1
            )
    
    def test_get_transactions_by_category_with_limit(self):
        """Test that limit works for category queries"""
        mock_db = Mock()
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all = Mock(return_value=[])
        
        result = get_transactions_by_category(mock_db, user_id=1, category="Stock Purchase", limit=100, offset=0)
        
        assert result == []
        mock_query.limit.assert_called_once_with(100)
    
    def test_get_transactions_by_category_invalid_limit(self):
        """Test that invalid limit raises ValidationError"""
        mock_db = Mock()
        
        with pytest.raises(ValidationError, match="limit must be between 0 and 1000"):
            get_transactions_by_category(mock_db, limit=1500)
    
    @patch('src.database.queries.get_portfolio_by_id')
    def test_get_portfolio_transaction_history_with_limit(self, mock_get_portfolio):
        """Test that limit works for portfolio transaction history"""
        mock_db = Mock()
        mock_portfolio = Mock()
        mock_portfolio.user_id = 1
        mock_get_portfolio.return_value = mock_portfolio
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all = Mock(return_value=[])
        
        result = get_portfolio_transaction_history(mock_db, portfolio_id=1, limit=200, offset=0)
        
        assert result == []
        mock_query.limit.assert_called_once_with(200)
    
    def test_get_portfolio_transaction_history_invalid_limit(self):
        """Test that invalid limit raises ValidationError"""
        mock_db = Mock()
        
        with pytest.raises(ValidationError, match="limit must be between 0 and 1000"):
            get_portfolio_transaction_history(mock_db, portfolio_id=1, limit=5000)
    
    def test_get_market_data_in_range_with_limit(self):
        """Test that limit works for market data range queries"""
        mock_db = Mock()
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all = Mock(return_value=[])
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = get_market_data_in_range(
            mock_db, start_date=start_date, end_date=end_date, limit=500, offset=0
        )
        
        assert result == []
        mock_query.limit.assert_called_once_with(500)


class TestQueryErrorHandling:
    """Tests for error handling in query functions"""
    
    def test_get_transactions_with_filters_validation_error_amount_range(self):
        """Test get_transactions_with_filters with invalid amount range"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, min_amount=100, max_amount=50)
        
        assert "min_amount cannot be greater than max_amount" in str(exc_info.value)
    
    def test_get_transactions_with_filters_validation_error_risk_score_range(self):
        """Test get_transactions_with_filters with invalid risk score range"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, min_risk_score=0.8, max_risk_score=0.5)
        
        assert "min_risk_score cannot be greater than max_risk_score" in str(exc_info.value)
    
    def test_get_transactions_with_filters_validation_error_date_range(self):
        """Test get_transactions_with_filters with invalid date range"""
        mock_db = MagicMock()
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(days=1)
        
        with pytest.raises(ValidationError) as exc_info:
            get_transactions_with_filters(mock_db, start_date=start_date, end_date=end_date)
        
        assert "start_date cannot be greater than end_date" in str(exc_info.value)
    
    def test_get_transactions_with_filters_operational_error(self):
        """Test get_transactions_with_filters with OperationalError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            get_transactions_with_filters(mock_db, user_id=1)
        
        assert "Database connection failed" in str(exc_info.value)
    
    def test_get_transactions_with_filters_sqlalchemy_error(self):
        """Test get_transactions_with_filters with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError) as exc_info:
            get_transactions_with_filters(mock_db, user_id=1)
        
        assert "Failed to query transactions" in str(exc_info.value)
    
    def test_get_transactions_with_filters_unexpected_error(self):
        """Test get_transactions_with_filters with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError) as exc_info:
            get_transactions_with_filters(mock_db, user_id=1)
        
        assert "Unexpected error querying transactions" in str(exc_info.value)
    
    def test_get_transaction_by_id_validation_error(self):
        """Test get_transaction_by_id with invalid transaction_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_transaction_by_id(mock_db, transaction_id=0)
        
        assert "transaction_id must be positive" in str(exc_info.value)
    
    def test_get_transaction_by_id_operational_error(self):
        """Test get_transaction_by_id with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_transaction_by_id(mock_db, transaction_id=1)
    
    def test_get_transaction_by_id_sqlalchemy_error(self):
        """Test get_transaction_by_id with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_transaction_by_id(mock_db, transaction_id=1)
    
    def test_get_user_transaction_count_validation_error(self):
        """Test get_user_transaction_count with invalid user_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_user_transaction_count(mock_db, user_id=0)
        
        assert "user_id must be positive" in str(exc_info.value)
    
    def test_get_transactions_by_user_and_period_validation_errors(self):
        """Test get_transactions_by_user_and_period with various validation errors"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Test invalid user_id
        with pytest.raises(ValidationError):
            get_transactions_by_user_and_period(mock_db, user_id=0, start_date=start_date, end_date=end_date)
        
        # Test invalid date range
        with pytest.raises(ValidationError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=end_date, end_date=start_date)
        
        # Test invalid limit
        with pytest.raises(ValidationError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date, limit=2000)
        
        # Test invalid offset
        with pytest.raises(ValidationError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date, offset=-1)
    
    def test_get_transactions_by_user_and_period_operational_error(self):
        """Test get_transactions_by_user_and_period with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        with pytest.raises(DatabaseConnectionError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date)
    
    def test_get_transaction_risk_distribution_validation_error(self):
        """Test get_transaction_risk_distribution with invalid user_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError):
            get_transaction_risk_distribution(mock_db, user_id=0)
    
    def test_get_transaction_risk_distribution_no_results(self):
        """Test get_transaction_risk_distribution with no results"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = get_transaction_risk_distribution(mock_db, user_id=1)
        
        assert len(result) == 1
        assert result[0]['count'] == 0
        assert result[0]['avg_risk'] == 0.0
    
    def test_get_transaction_risk_distribution_operational_error(self):
        """Test get_transaction_risk_distribution with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_transaction_risk_distribution(mock_db, user_id=1)
    
    def test_get_transactions_by_category_validation_errors(self):
        """Test get_transactions_by_category with validation errors"""
        mock_db = MagicMock()
        
        # Test invalid user_id
        with pytest.raises(ValidationError):
            get_transactions_by_category(mock_db, user_id=0)
        
        # Test invalid limit
        with pytest.raises(ValidationError):
            get_transactions_by_category(mock_db, limit=2000)
        
        # Test invalid offset
        with pytest.raises(ValidationError):
            get_transactions_by_category(mock_db, offset=-1)
    
    def test_get_transactions_by_category_operational_error(self):
        """Test get_transactions_by_category with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_transactions_by_category(mock_db, user_id=1)
    
    def test_get_portfolio_by_id_validation_error(self):
        """Test get_portfolio_by_id with invalid portfolio_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_portfolio_by_id(mock_db, portfolio_id=0)
        
        assert "portfolio_id must be positive" in str(exc_info.value)
    
    def test_get_portfolio_by_id_operational_error(self):
        """Test get_portfolio_by_id with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_portfolio_by_id(mock_db, portfolio_id=1)
    
    def test_get_user_portfolios_validation_error(self):
        """Test get_user_portfolios with invalid user_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError):
            get_user_portfolios(mock_db, user_id=0)
    
    def test_get_user_portfolios_operational_error(self):
        """Test get_user_portfolios with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_user_portfolios(mock_db, user_id=1)
    
    def test_get_portfolio_transaction_history_validation_error(self):
        """Test get_portfolio_transaction_history with invalid portfolio_id"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        with pytest.raises(ValidationError):
            get_portfolio_transaction_history(mock_db, portfolio_id=0, start_date=start_date, end_date=end_date)
    
    def test_get_portfolio_transaction_history_operational_error(self):
        """Test get_portfolio_transaction_history with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        with pytest.raises(DatabaseConnectionError):
            get_portfolio_transaction_history(mock_db, portfolio_id=1, start_date=start_date, end_date=end_date)
    
    def test_get_portfolio_assets_validation_error(self):
        """Test get_portfolio_assets with invalid portfolio_id"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError):
            get_portfolio_assets(mock_db, portfolio_id=0)
    
    def test_get_portfolio_assets_operational_error(self):
        """Test get_portfolio_assets with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_portfolio_assets(mock_db, portfolio_id=1)
    
    def test_get_market_data_by_symbols_validation_error(self):
        """Test get_market_data_by_symbols with empty symbols"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_market_data_by_symbols(mock_db, symbols=[])
        
        assert "symbols list cannot be empty" in str(exc_info.value)
    
    def test_get_market_data_by_symbols_operational_error(self):
        """Test get_market_data_by_symbols with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_market_data_by_symbols(mock_db, symbols=["AAPL"])
    
    def test_get_latest_price_per_symbol_validation_error(self):
        """Test get_latest_price_per_symbol with empty symbol"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_latest_price_per_symbol(mock_db, symbol="")
        
        assert "symbol cannot be empty" in str(exc_info.value)
    
    def test_get_latest_price_per_symbol_operational_error(self):
        """Test get_latest_price_per_symbol with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_latest_price_per_symbol(mock_db, symbol="AAPL")
    
    def test_get_price_history_validation_errors(self):
        """Test get_price_history - no validation errors, function accepts any input"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Function doesn't validate - it just executes the query
        result = get_price_history(mock_db, symbol="", start_date=start_date, end_date=end_date)
        assert isinstance(result, list)
        
        # Even with invalid date range, function doesn't validate
        result = get_price_history(mock_db, symbol="AAPL", start_date=end_date, end_date=start_date)
        assert isinstance(result, list)
    
    def test_get_price_history_operational_error(self):
        """Test get_price_history - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_price_history(mock_db, symbol="AAPL", start_date=start_date, end_date=end_date)
    
    def test_get_volume_statistics_validation_error(self):
        """Test get_volume_statistics - no validation, function accepts any input"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_result = Mock()
        mock_result.avg_volume = None
        mock_result.min_volume = None
        mock_result.max_volume = None
        mock_result.total_volume = None
        mock_result.count = 0
        mock_query.first.return_value = mock_result
        
        # Function doesn't validate empty symbol
        result = get_volume_statistics(mock_db, symbol="")
        assert result['symbol'] == ""
    
    def test_get_volume_statistics_operational_error(self):
        """Test get_volume_statistics - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_volume_statistics(mock_db, symbol="AAPL")
    
    def test_get_price_changes_validation_error(self):
        """Test get_price_changes - no validation, function accepts any symbol"""
        mock_db = MagicMock()
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_latest:
            mock_latest.return_value = None
            
            # Function doesn't validate empty symbol, just returns default
            result = get_price_changes(mock_db, symbol="")
            assert result['symbol'] == ""
            assert result['price_change'] == 0.0
    
    def test_get_price_changes_operational_error(self):
        """Test get_price_changes - errors from get_latest_price_per_symbol propagate"""
        mock_db = MagicMock()
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_latest:
            mock_latest.side_effect = OperationalError("Connection lost", None, None)
            
            # Errors propagate from get_latest_price_per_symbol
            with pytest.raises(OperationalError):
                get_price_changes(mock_db, symbol="AAPL")
    
    def test_get_top_movers_validation_errors(self):
        """Test get_top_movers - no validation, function accepts any limit"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = []
        
        # When no symbols, function returns empty list (no calls to get_price_changes)
        result = get_top_movers(mock_db, limit=0)
        assert isinstance(result, list)
        assert len(result) == 0
        
        result = get_top_movers(mock_db, limit=101)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_top_movers_with_movers(self):
        """Test get_top_movers with actual movers"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("AAPL",), ("GOOGL",)]
        
        with patch('src.database.queries.get_price_changes') as mock_changes:
            mock_changes.side_effect = [
                {"symbol": "AAPL", "percent_change": 5.0},
                {"symbol": "GOOGL", "percent_change": -3.0}
            ]
            
            result = get_top_movers(mock_db, limit=10, direction="both")
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_get_top_movers_direction_filters(self):
        """Test get_top_movers with different direction filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [("AAPL",), ("GOOGL",)]
        
        with patch('src.database.queries.get_price_changes') as mock_changes:
            # Test "up" direction - only positive changes
            mock_changes.side_effect = [
                {"symbol": "AAPL", "percent_change": 5.0},
                {"symbol": "GOOGL", "percent_change": -3.0}
            ]
            result = get_top_movers(mock_db, limit=10, direction="up")
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['symbol'] == "AAPL"
            
            # Test "down" direction - only negative changes
            mock_changes.side_effect = [
                {"symbol": "AAPL", "percent_change": 5.0},
                {"symbol": "GOOGL", "percent_change": -3.0}
            ]
            result = get_top_movers(mock_db, limit=10, direction="down")
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['symbol'] == "GOOGL"
    
    def test_get_market_data_in_range_validation_errors(self):
        """Test get_market_data_in_range with validation errors"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Function doesn't validate date range, only limit and offset
        # Test invalid limit
        with pytest.raises(ValidationError) as exc_info:
            get_market_data_in_range(mock_db, start_date=start_date, end_date=end_date, limit=2000)
        assert "limit must be between 0 and 1000" in str(exc_info.value)
        
        # Test invalid offset
        with pytest.raises(ValidationError) as exc_info:
            get_market_data_in_range(mock_db, start_date=start_date, end_date=end_date, offset=-1)
        assert "offset must be non-negative" in str(exc_info.value)
    
    def test_get_market_data_in_range_with_symbols(self):
        """Test get_market_data_in_range with symbols filter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        result = get_market_data_in_range(mock_db, start_date=start_date, end_date=end_date, symbols=["AAPL", "GOOGL"])
        assert isinstance(result, list)
    
    def test_get_latest_market_data_validation_error(self):
        """Test get_latest_market_data - no validation, accepts empty symbols list"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = datetime.utcnow()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        # Function doesn't validate empty symbols, just returns empty list
        result = get_latest_market_data(mock_db, symbols=[])
        assert isinstance(result, list)
    
    def test_get_latest_market_data_operational_error(self):
        """Test get_latest_market_data - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_latest_market_data(mock_db, symbols=["AAPL"])
    
    def test_aggregate_by_symbol_validation_error(self):
        """Test aggregate_by_symbol - no validation, function doesn't take symbols parameter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_result = Mock()
        mock_result.symbol = "AAPL"
        mock_result.avg_price = 100.0
        mock_result.min_price = 90.0
        mock_result.max_price = 110.0
        mock_result.avg_volume = 1000.0
        mock_result.count = 10
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        
        # Function doesn't validate, just executes query
        result = aggregate_by_symbol(mock_db)
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_aggregate_by_symbol_with_date_filters(self):
        """Test aggregate_by_symbol with date filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_result = Mock()
        mock_result.symbol = "AAPL"
        mock_result.avg_price = 100.0
        mock_result.min_price = 90.0
        mock_result.max_price = 110.0
        mock_result.avg_volume = 1000.0
        mock_result.count = 10
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = aggregate_by_symbol(mock_db, start_date=start_date, end_date=end_date)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['symbol'] == "AAPL"
    
    def test_aggregate_by_time_period_validation_errors(self):
        """Test aggregate_by_time_period - no validation, function doesn't take symbols parameter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        # Function doesn't validate date range or symbols (doesn't even take symbols)
        result = aggregate_by_time_period(mock_db, period="day", start_date=start_date, end_date=end_date)
        assert isinstance(result, list)
    
    def test_aggregate_by_time_period_with_symbol_filter(self):
        """Test aggregate_by_time_period with symbol filter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_result = Mock()
        mock_result.period = datetime.utcnow()
        mock_result.avg_price = 100.0
        mock_result.min_price = 90.0
        mock_result.max_price = 110.0
        mock_result.total_volume = 10000
        mock_result.count = 10
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        
        result = aggregate_by_time_period(mock_db, period="day", symbol="AAPL")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['avg_price'] == 100.0
    
    def test_get_latest_prices_dict_validation_error(self):
        """Test get_latest_prices_dict - no validation, accepts empty symbols"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        
        # Function doesn't validate empty symbols, just returns empty dict
        result = get_latest_prices_dict(mock_db, symbols=[])
        assert result == {}
    
    def test_get_latest_prices_dict_operational_error(self):
        """Test get_latest_prices_dict - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_latest_prices_dict(mock_db, symbols=["AAPL"])
    
    def test_get_price_history_with_date_filters(self):
        """Test get_price_history with date filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        # Test with date filters
        result = get_price_history(mock_db, symbol="AAPL", start_date=start_date, end_date=end_date)
        assert isinstance(result, list)
        
        # Test with limit
        result = get_price_history(mock_db, symbol="AAPL", limit=100)
        assert isinstance(result, list)
        
        # Test without filters
        result = get_price_history(mock_db, symbol="AAPL")
        assert isinstance(result, list)
    
    def test_get_price_history_operational_error(self):
        """Test get_price_history - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_price_history(mock_db, symbol="AAPL")
    
    def test_get_volume_statistics_with_date_filters(self):
        """Test get_volume_statistics with date filters"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_result = Mock()
        mock_result.avg_volume = 1000.0
        mock_result.min_volume = 500
        mock_result.max_volume = 2000
        mock_result.total_volume = 10000
        mock_result.count = 10
        mock_query.first.return_value = mock_result
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = get_volume_statistics(mock_db, symbol="AAPL", start_date=start_date, end_date=end_date)
        
        assert result['symbol'] == "AAPL"
        assert result['avg_volume'] == 1000.0
        assert result['count'] == 10
    
    def test_get_volume_statistics_no_results(self):
        """Test get_volume_statistics with no results - function will fail on None result"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Function doesn't handle None result, will raise AttributeError
        with pytest.raises(AttributeError):
            get_volume_statistics(mock_db, symbol="AAPL")
    
    def test_get_volume_statistics_operational_error(self):
        """Test get_volume_statistics - no error handling, errors propagate"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        # Function doesn't catch errors, they propagate
        with pytest.raises(OperationalError):
            get_volume_statistics(mock_db, symbol="AAPL")
    
    def test_get_portfolio_assets_with_assets(self):
        """Test get_portfolio_assets with portfolio that has assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = {"AAPL": 100, "GOOGL": 50}
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            result = get_portfolio_assets(mock_db, portfolio_id=1)
            
            assert result == {"AAPL": 100, "GOOGL": 50}
    
    def test_get_portfolio_assets_no_assets(self):
        """Test get_portfolio_assets with portfolio that has no assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = None
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            result = get_portfolio_assets(mock_db, portfolio_id=1)
            
            assert result == {}
    
    def test_get_historical_portfolio_values_with_portfolio(self):
        """Test get_historical_portfolio_values with portfolio"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        mock_portfolio.total_value = 10000.0
        mock_portfolio.last_updated = datetime.utcnow()
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            result = get_historical_portfolio_values(mock_db, portfolio_id=1)
            
            assert len(result) == 1
            assert result[0]['portfolio_id'] == 1
            assert result[0]['total_value'] == 10000.0
    
    def test_get_portfolio_holdings_current_prices_dict_assets_with_prices(self):
        """Test get_portfolio_holdings_current_prices with dict assets and prices"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = {"AAPL": 100, "GOOGL": 50}
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            with patch('src.database.queries.get_latest_price_per_symbol') as mock_price:
                mock_price_aapl = Mock()
                mock_price_aapl.price = 150.0
                mock_price_googl = Mock()
                mock_price_googl.price = 200.0
                mock_price.side_effect = [mock_price_aapl, mock_price_googl]
                
                result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
                
                assert "AAPL" in result
                assert "GOOGL" in result
                assert result["AAPL"] == 150.0
                assert result["GOOGL"] == 200.0
    
    def test_get_portfolio_holdings_current_prices_list_assets_with_prices(self):
        """Test get_portfolio_holdings_current_prices with list assets and prices"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = [{"symbol": "AAPL", "shares": 100}, {"symbol": "GOOGL", "shares": 50}]
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            with patch('src.database.queries.get_latest_price_per_symbol') as mock_price:
                mock_price_aapl = Mock()
                mock_price_aapl.price = 150.0
                mock_price_googl = Mock()
                mock_price_googl.price = 200.0
                mock_price.side_effect = [mock_price_aapl, mock_price_googl]
                
                result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
                
                assert "AAPL" in result
                assert "GOOGL" in result
    
    def test_get_portfolio_holdings_current_prices_no_price_available(self):
        """Test get_portfolio_holdings_current_prices when price not available"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = {"AAPL": 100}
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            with patch('src.database.queries.get_latest_price_per_symbol') as mock_price:
                mock_price.return_value = None  # No price available
                
                result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
                
                assert result == {}  # Should return empty dict when no prices
    
    def test_get_price_changes_with_historical_data(self):
        """Test get_price_changes with historical data"""
        mock_db = MagicMock()
        mock_latest = Mock()
        mock_latest.price = 150.0
        mock_latest.timestamp = datetime.utcnow()
        
        mock_historical = Mock()
        mock_historical.price = 100.0
        mock_historical.timestamp = datetime.utcnow() - timedelta(hours=24)
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_get_latest:
            mock_get_latest.return_value = mock_latest
            
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = mock_historical
            
            result = get_price_changes(mock_db, symbol="AAPL", period_hours=24)
            
            assert result['symbol'] == "AAPL"
            assert result['current_price'] == 150.0
            assert result['previous_price'] == 100.0
            assert result['price_change'] == 50.0
            assert result['percent_change'] == 50.0
    
    def test_get_price_changes_zero_historical_price(self):
        """Test get_price_changes when historical price is zero"""
        mock_db = MagicMock()
        mock_latest = Mock()
        mock_latest.price = 150.0
        mock_latest.timestamp = datetime.utcnow()
        
        mock_historical = Mock()
        mock_historical.price = 0.0
        mock_historical.timestamp = datetime.utcnow() - timedelta(hours=24)
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_get_latest:
            mock_get_latest.return_value = mock_latest
            
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = mock_historical
            
            result = get_price_changes(mock_db, symbol="AAPL", period_hours=24)
            
            assert result['percent_change'] == 0.0  # Should be 0 when historical price is 0
    
    def test_get_portfolio_holdings_current_prices_no_portfolio(self):
        """Test get_portfolio_holdings_current_prices with no portfolio"""
        mock_db = MagicMock()
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = None
            
            result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=999)
            
            assert result == {}
    
    def test_get_portfolio_holdings_current_prices_no_assets(self):
        """Test get_portfolio_holdings_current_prices with portfolio but no assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = None
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
            
            assert result == {}
    
    def test_get_portfolio_holdings_current_prices_dict_assets(self):
        """Test get_portfolio_holdings_current_prices with dict assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = {"AAPL": 100, "GOOGL": 50}
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            with patch('src.database.queries.get_latest_price_per_symbol') as mock_price:
                mock_price_data = Mock()
                mock_price_data.price = 150.0
                mock_price.return_value = mock_price_data
                
                result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
                
                assert "AAPL" in result
                assert "GOOGL" in result
    
    def test_get_portfolio_holdings_current_prices_list_assets(self):
        """Test get_portfolio_holdings_current_prices with list assets"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = [{"symbol": "AAPL", "shares": 100}, {"symbol": "GOOGL", "shares": 50}]
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            with patch('src.database.queries.get_latest_price_per_symbol') as mock_price:
                mock_price_data = Mock()
                mock_price_data.price = 150.0
                mock_price.return_value = mock_price_data
                
                result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
                
                assert "AAPL" in result
                assert "GOOGL" in result
    
    def test_get_portfolio_holdings_current_prices_no_symbols(self):
        """Test get_portfolio_holdings_current_prices with assets but no valid symbols"""
        mock_db = MagicMock()
        mock_portfolio = Mock()
        mock_portfolio.assets = [{"no_symbol": "value"}]  # No 'symbol' key
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = mock_portfolio
            
            result = get_portfolio_holdings_current_prices(mock_db, portfolio_id=1)
            
            assert result == {}
    
    def test_get_historical_portfolio_values_no_portfolio(self):
        """Test get_historical_portfolio_values with no portfolio"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = None
            
            result = get_historical_portfolio_values(mock_db, portfolio_id=999, start_date=start_date, end_date=end_date)
            
            assert result == []
    
    def test_get_historical_portfolio_values_operational_error(self):
        """Test get_historical_portfolio_values - no error handling, errors from get_portfolio_by_id propagate"""
        mock_db = MagicMock()
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.side_effect = OperationalError("Connection lost", None, None)
            
            # Errors from get_portfolio_by_id propagate
            with pytest.raises(OperationalError):
                get_historical_portfolio_values(mock_db, portfolio_id=1, start_date=start_date, end_date=end_date)
    
    def test_get_market_data_by_symbols_no_valid_symbols(self):
        """Test get_market_data_by_symbols with no valid symbols after normalization"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError) as exc_info:
            get_market_data_by_symbols(mock_db, symbols=["", "  ", None])
        
        assert "No valid symbols provided" in str(exc_info.value)
    
    def test_get_market_data_by_symbols_negative_limit(self):
        """Test get_market_data_by_symbols with negative limit_per_symbol"""
        mock_db = MagicMock()
        
        with pytest.raises(ValidationError):
            get_market_data_by_symbols(mock_db, symbols=["AAPL"], limit_per_symbol=-1)
    
    def test_get_market_data_by_symbols_sqlalchemy_error(self):
        """Test get_market_data_by_symbols with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_market_data_by_symbols(mock_db, symbols=["AAPL"])
    
    def test_get_market_data_by_symbols_unexpected_error(self):
        """Test get_market_data_by_symbols with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_market_data_by_symbols(mock_db, symbols=["AAPL"])
    
    
    def test_aggregate_by_time_period_different_periods(self):
        """Test aggregate_by_time_period with different period values"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        # Test hour period
        aggregate_by_time_period(mock_db, period="hour")
        
        # Test week period
        aggregate_by_time_period(mock_db, period="week")
        
        # Test month period
        aggregate_by_time_period(mock_db, period="month")
        
        # Test invalid period (should default to day)
        aggregate_by_time_period(mock_db, period="invalid")
        
        # Test with symbol filter
        aggregate_by_time_period(mock_db, period="day", symbol="AAPL")
        
        # Test with date filters
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        aggregate_by_time_period(mock_db, period="day", start_date=start_date, end_date=end_date)
    
    
    def test_get_portfolio_transaction_history_validation_errors(self):
        """Test get_portfolio_transaction_history with validation errors"""
        mock_db = MagicMock()
        
        # Test invalid limit
        with pytest.raises(ValidationError):
            get_portfolio_transaction_history(mock_db, portfolio_id=1, limit=2000)
        
        with pytest.raises(ValidationError):
            get_portfolio_transaction_history(mock_db, portfolio_id=1, limit=-1)
        
        # Test invalid offset
        with pytest.raises(ValidationError):
            get_portfolio_transaction_history(mock_db, portfolio_id=1, offset=-1)
    
    def test_get_portfolio_transaction_history_no_portfolio(self):
        """Test get_portfolio_transaction_history with no portfolio"""
        mock_db = MagicMock()
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get:
            mock_get.return_value = None
            
            result = get_portfolio_transaction_history(mock_db, portfolio_id=999)
            
            assert result == []
    
    def test_get_transactions_with_filters_currency(self):
        """Test filtering transactions by currency"""
        mock_db = MagicMock()
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.currency = "EUR"
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5
            tx.timestamp = datetime.utcnow()
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, currency="EUR")
        
        assert len(result) == 3
        assert all(tx.currency == "EUR" for tx in result)
    
    def test_get_transactions_with_filters_risk_score_filters(self):
        """Test filtering transactions by risk score range"""
        mock_db = MagicMock()
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.risk_score = 0.3 + (i * 0.2)
            tx.user_id = 1
            tx.id = i + 1
            tx.amount = 100.0
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.timestamp = datetime.utcnow()
            mock_transactions.append(tx)
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_db.query.return_value = mock_query
        
        result = get_transactions_with_filters(mock_db, min_risk_score=0.3, max_risk_score=0.7)
        
        assert len(result) == 3
        assert all(0.3 <= tx.risk_score <= 0.7 for tx in result)
    
    def test_get_transaction_by_id_sqlalchemy_error(self):
        """Test get_transaction_by_id with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_transaction_by_id(mock_db, transaction_id=1)
    
    def test_get_transaction_by_id_unexpected_error(self):
        """Test get_transaction_by_id with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_transaction_by_id(mock_db, transaction_id=1)
    
    def test_get_user_transaction_count_operational_error(self):
        """Test get_user_transaction_count with OperationalError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("Connection lost", None, None)
        
        with pytest.raises(DatabaseConnectionError):
            get_user_transaction_count(mock_db, user_id=1)
    
    def test_get_user_transaction_count_sqlalchemy_error(self):
        """Test get_user_transaction_count with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_user_transaction_count(mock_db, user_id=1)
    
    def test_get_user_transaction_count_unexpected_error(self):
        """Test get_user_transaction_count with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_user_transaction_count(mock_db, user_id=1)
    
    def test_get_transactions_by_user_and_period_sqlalchemy_error(self):
        """Test get_transactions_by_user_and_period with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.side_effect = SQLAlchemyError("SQL error", None, None)
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        with pytest.raises(DatabaseQueryError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date)
    
    def test_get_transactions_by_user_and_period_unexpected_error(self):
        """Test get_transactions_by_user_and_period with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        
        with pytest.raises(DatabaseError):
            get_transactions_by_user_and_period(mock_db, user_id=1, start_date=start_date, end_date=end_date)
    
    def test_get_transaction_risk_distribution_sqlalchemy_error(self):
        """Test get_transaction_risk_distribution with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_db.query.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_transaction_risk_distribution(mock_db, user_id=1)
    
    def test_get_transaction_risk_distribution_unexpected_error(self):
        """Test get_transaction_risk_distribution with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_transaction_risk_distribution(mock_db, user_id=1)
    
    def test_get_transactions_by_category_sqlalchemy_error(self):
        """Test get_transactions_by_category with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_transactions_by_category(mock_db, user_id=1)
    
    def test_get_transactions_by_category_unexpected_error(self):
        """Test get_transactions_by_category with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_transactions_by_category(mock_db, user_id=1)
    
    def test_get_portfolio_by_id_sqlalchemy_error(self):
        """Test get_portfolio_by_id with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_portfolio_by_id(mock_db, portfolio_id=1)
    
    def test_get_portfolio_by_id_unexpected_error(self):
        """Test get_portfolio_by_id with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_portfolio_by_id(mock_db, portfolio_id=1)
    
    def test_get_user_portfolios_sqlalchemy_error(self):
        """Test get_user_portfolios with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_user_portfolios(mock_db, user_id=1)
    
    def test_get_user_portfolios_unexpected_error(self):
        """Test get_user_portfolios with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_user_portfolios(mock_db, user_id=1)
    
    def test_get_market_data_by_symbols_with_limit(self):
        """Test get_market_data_by_symbols with limit_per_symbol"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        result = get_market_data_by_symbols(mock_db, symbols=["AAPL", "GOOGL"], limit_per_symbol=10)
        assert isinstance(result, list)
    
    def test_get_latest_price_per_symbol_sqlalchemy_error(self):
        """Test get_latest_price_per_symbol with SQLAlchemyError"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.side_effect = SQLAlchemyError("SQL error", None, None)
        
        with pytest.raises(DatabaseQueryError):
            get_latest_price_per_symbol(mock_db, symbol="AAPL")
    
    def test_get_latest_price_per_symbol_unexpected_error(self):
        """Test get_latest_price_per_symbol with unexpected error"""
        mock_db = MagicMock()
        mock_db.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(DatabaseError):
            get_latest_price_per_symbol(mock_db, symbol="AAPL")
    
    def test_get_price_changes_no_historical(self):
        """Test get_price_changes when no historical data"""
        mock_db = MagicMock()
        mock_latest = Mock()
        mock_latest.price = 150.0
        mock_latest.timestamp = datetime.utcnow()
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_get_latest:
            mock_get_latest.return_value = mock_latest
            
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = None  # No historical data
            
            result = get_price_changes(mock_db, symbol="AAPL", period_hours=24)
            
            assert result['symbol'] == "AAPL"
            assert result['price_change'] == 0.0
            assert result['percent_change'] == 0.0
    
    def test_get_price_changes_with_historical_price_zero(self):
        """Test get_price_changes when historical price is zero"""
        mock_db = MagicMock()
        mock_latest = Mock()
        mock_latest.price = 150.0
        mock_latest.timestamp = datetime.utcnow()
        
        mock_historical = Mock()
        mock_historical.price = 0.0
        mock_historical.timestamp = datetime.utcnow() - timedelta(hours=24)
        
        with patch('src.database.queries.get_latest_price_per_symbol') as mock_get_latest:
            mock_get_latest.return_value = mock_latest
            
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.first.return_value = mock_historical
            
            result = get_price_changes(mock_db, symbol="AAPL", period_hours=24)
            
            assert result['symbol'] == "AAPL"
            assert result['percent_change'] == 0.0  # Should be 0 when historical price is 0
    
    def test_get_latest_market_data_with_limit(self):
        """Test get_latest_market_data with limit"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = datetime.utcnow()
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        result = get_latest_market_data(mock_db, symbols=["AAPL"], limit=10)
        assert isinstance(result, list)
    
    def test_get_latest_market_data_no_timestamp(self):
        """Test get_latest_market_data when no timestamp exists"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = None  # No timestamp
        
        result = get_latest_market_data(mock_db, symbols=["AAPL"])
        assert result == []
    
    def test_get_latest_market_data_with_symbols(self):
        """Test get_latest_market_data with symbols filter"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.scalar.return_value = datetime.utcnow()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        
        result = get_latest_market_data(mock_db, symbols=["AAPL", "GOOGL"])
        assert isinstance(result, list)
    
