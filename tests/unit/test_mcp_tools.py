"""
Unit tests for MCP tools with mocked database responses
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.mcp.tools import list_tools, call_tool
from src.utils.exceptions import ValidationError, DatabaseConnectionError, DatabaseQueryError
from src.auth.permissions import Role


class TestMCPToolsList:
    """Tests for listing MCP tools (no database mocking needed)"""
    
    def test_list_tools_returns_tools(self):
        """Test that list_tools returns a list of tools"""
        tools = list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 3
    
    def test_list_tools_contains_query_transactions(self):
        """Test that query_transactions tool is in the list"""
        tools = list_tools()
        tool_names = [tool['name'] for tool in tools]
        assert "query_transactions" in tool_names
    
    def test_list_tools_contains_analyze_risk_metrics(self):
        """Test that analyze_risk_metrics tool is in the list"""
        tools = list_tools()
        tool_names = [tool['name'] for tool in tools]
        assert "analyze_risk_metrics" in tool_names
    
    def test_list_tools_contains_get_market_summary(self):
        """Test that get_market_summary tool is in the list"""
        tools = list_tools()
        tool_names = [tool['name'] for tool in tools]
        assert "get_market_summary" in tool_names
    
    def test_list_tools_has_correct_structure(self):
        """Test that tools have correct structure"""
        tools = list_tools()
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            assert 'type' in tool['inputSchema']
            assert tool['inputSchema']['type'] == 'object'


class TestQueryTransactionsToolMocked:
    """Tests for query_transactions MCP tool with mocked database"""
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.get_transactions_with_filters')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_success(self, mock_get_user, mock_query, mock_get_db):
        """Test successful query_transactions call with mocked database"""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        # Mock user context (admin role)
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        # Mock transaction data
        mock_transaction = Mock()
        mock_transaction.id = 1
        mock_transaction.user_id = 1
        mock_transaction.amount = 100.0
        mock_transaction.currency = "USD"
        mock_transaction.category = "Stock Purchase"
        mock_transaction.risk_score = 0.5
        mock_transaction.timestamp = datetime.utcnow()
        mock_query.return_value = [mock_transaction]
        
        # Call tool with admin context
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", {"user_id": 1, "limit": 10}, context=context)
        
        # Assertions
        assert result['isError'] is False
        assert len(result['content']) > 0
        assert 'Transaction ID: 1' in result['content'][0]['text']
        mock_query.assert_called_once()
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.get_transactions_with_filters')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_with_filters(self, mock_get_user, mock_query, mock_get_db):
        """Test query_transactions with various filters"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        mock_transactions = []
        for i in range(3):
            tx = Mock()
            tx.id = i + 1
            tx.user_id = 1
            tx.amount = 100.0 * (i + 1)
            tx.currency = "USD"
            tx.category = "Stock Purchase"
            tx.risk_score = 0.5 + (i * 0.1)
            tx.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_transactions.append(tx)
        
        mock_query.return_value = mock_transactions
        
        arguments = {
            "user_id": 1,
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "min_risk_score": 0.5,
            "limit": 10
        }
        
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", arguments, context=context)
        
        assert result['isError'] is False
        assert len(result['content']) == 3
        mock_query.assert_called_once()
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_no_results(self, mock_get_user, mock_get_db):
        """Test query_transactions with no matching results"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_transactions_with_filters') as mock_query:
            mock_query.return_value = []
            
            context = {"token": "admin_token"}
            result = call_tool("query_transactions", {"user_id": 1}, context=context)
            
            assert result['isError'] is False
            assert 'No transactions found' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_date_format(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid date format"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool(
            "query_transactions",
            {"start_date": "invalid-date", "user_id": 1},
            context=context
        )
        
        assert result['isError'] is True
        assert 'Invalid start_date format' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_risk_score(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid risk score"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool(
            "query_transactions",
            {"min_risk_score": 1.5, "user_id": 1},  # Invalid: > 1.0
            context=context
        )
        
        assert result['isError'] is True
        assert 'min_risk_score must be between 0.0 and 1.0' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_database_error(self, mock_get_user, mock_get_db):
        """Test query_transactions with database error"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_transactions_with_filters') as mock_query:
            mock_query.side_effect = DatabaseQueryError("Database connection failed", None)
            
            context = {"token": "admin_token"}
            result = call_tool("query_transactions", {"user_id": 1}, context=context)
            
            assert result['isError'] is True
            assert 'Database error' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_viewer_permission_denied(self, mock_get_user, mock_get_db):
        """Test query_transactions with viewer role (should fail)"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        context = {"token": "viewer_token"}
        result = call_tool("query_transactions", {"user_id": 1}, context=context)
        
        assert result['isError'] is True
        assert 'Missing required permissions' in result['content'][0]['text']


class TestAnalyzeRiskMetricsToolMocked:
    """Tests for analyze_risk_metrics MCP tool with mocked database"""
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.get_portfolio_by_id')
    @patch('src.mcp.tools.get_portfolio_transaction_history')
    @patch('src.mcp.tools.get_latest_prices_dict')
    @patch('src.mcp.tools.RiskAnalyzer')
    @patch('src.auth.rbac.get_user_from_context')
    def test_analyze_risk_metrics_success(self, mock_get_user, mock_analyzer_class, 
                                          mock_prices, mock_history, mock_portfolio, mock_get_db):
        """Test successful analyze_risk_metrics call"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "analyst",
            "roles": ["analyst"]
        }
        
        # Mock portfolio
        mock_portfolio_obj = Mock()
        mock_portfolio_obj.id = 2
        mock_portfolio_obj.user_id = 1
        mock_portfolio_obj.total_value = 10000.0
        mock_portfolio_obj.assets = {"AAPL": {"shares": 100, "price": 175.0}}
        mock_portfolio.return_value = mock_portfolio_obj
        
        # Mock transactions
        mock_transactions = []
        for i in range(5):
            tx = Mock()
            tx.__dict__ = {
                "id": i + 1,
                "amount": 100.0 * (i + 1),
                "timestamp": datetime.utcnow() - timedelta(days=i)
            }
            mock_transactions.append(tx)
        mock_history.return_value = mock_transactions
        
        # Mock prices
        mock_prices.return_value = {"AAPL": 175.0}
        
        # Mock risk analyzer
        mock_analyzer = Mock()
        mock_analyzer.calculate_all_metrics.return_value = {
            "portfolio_value": 17500.0,
            "volatility": 0.15,
            "sharpe_ratio": 1.5,
            "value_at_risk_95": -500.0,
            "average_return": 0.10,
            "max_drawdown": -0.05,
            "risk_level": "MEDIUM"
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        context = {"token": "analyst_token"}
        result = call_tool("analyze_risk_metrics", {"portfolio_id": 2, "period_days": 30}, context=context)
        
        assert result['isError'] is False
        assert 'Portfolio 2' in result['content'][0]['text']
        assert '17,500' in result['content'][0]['text'] or '17500' in result['content'][0]['text']
        assert 'MEDIUM' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.get_portfolio_by_id')
    @patch('src.auth.rbac.get_user_from_context')
    def test_analyze_risk_metrics_portfolio_not_found(self, mock_get_user, mock_portfolio, mock_get_db):
        """Test analyze_risk_metrics with non-existent portfolio"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "analyst",
            "roles": ["analyst"]
        }
        mock_portfolio.return_value = None
        
        context = {"token": "analyst_token"}
        result = call_tool("analyze_risk_metrics", {"portfolio_id": 999}, context=context)
        
        assert result['isError'] is True
        assert 'not found' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_analyze_risk_metrics_viewer_permission_denied(self, mock_get_user, mock_get_db):
        """Test analyze_risk_metrics with viewer role (should fail)"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        context = {"token": "viewer_token"}
        result = call_tool("analyze_risk_metrics", {"portfolio_id": 2}, context=context)
        
        assert result['isError'] is True
        assert 'Missing required permissions' in result['content'][0]['text']


class TestGetMarketSummaryToolMocked:
    """Tests for get_market_summary MCP tool with mocked database"""
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.aggregate_by_symbol')
    @patch('src.mcp.tools.get_latest_market_data')
    @patch('src.auth.rbac.get_user_from_context')
    def test_get_market_summary_success(self, mock_get_user, mock_latest, mock_aggregate, mock_get_db):
        """Test successful get_market_summary call"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        # Mock aggregated data
        mock_agg = [
            {
                'symbol': 'AAPL',
                'avg_price': 175.0,
                'min_price': 170.0,
                'max_price': 180.0,
                'avg_volume': 1000000,
                'count': 10
            },
            {
                'symbol': 'GOOGL',
                'avg_price': 140.0,
                'min_price': 135.0,
                'max_price': 145.0,
                'avg_volume': 2000000,
                'count': 15
            }
        ]
        mock_aggregate.return_value = mock_agg
        
        # Mock latest market data
        mock_data_aapl = Mock()
        mock_data_aapl.symbol = 'AAPL'
        mock_data_aapl.price = 175.5
        mock_data_googl = Mock()
        mock_data_googl.symbol = 'GOOGL'
        mock_data_googl.price = 140.2
        mock_latest.return_value = [mock_data_aapl, mock_data_googl]
        
        context = {"token": "viewer_token"}
        result = call_tool("get_market_summary", {}, context=context)
        
        assert result['isError'] is False
        assert len(result['content']) > 0
        assert 'AAPL' in result['content'][0]['text']
        assert 'GOOGL' in result['content'][0]['text']
        assert '175.50' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.aggregate_by_symbol')
    @patch('src.mcp.tools.get_latest_market_data')
    @patch('src.mcp.tools.aggregate_by_time_period')
    @patch('src.auth.rbac.get_user_from_context')
    def test_get_market_summary_with_period(self, mock_get_user, mock_time_agg, 
                                           mock_latest, mock_aggregate, mock_get_db):
        """Test get_market_summary with time period aggregation"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        mock_aggregate.return_value = []
        mock_latest.return_value = []
        mock_time_agg.return_value = [
            {
                'period': '2024-01-01',
                'avg_price': 175.0,
                'total_volume': 1000000
            }
        ]
        
        context = {"token": "viewer_token"}
        result = call_tool("get_market_summary", {"period": "week"}, context=context)
        
        assert result['isError'] is False
        mock_time_agg.assert_called_once()
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.mcp.tools.aggregate_by_symbol')
    @patch('src.mcp.tools.get_latest_market_data')
    @patch('src.auth.rbac.get_user_from_context')
    def test_get_market_summary_with_symbols(self, mock_get_user, mock_latest, mock_aggregate, mock_get_db):
        """Test get_market_summary with specific symbols"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 5,
            "username": "viewer",
            "roles": ["viewer"]
        }
        
        mock_agg = [
            {'symbol': 'AAPL', 'avg_price': 175.0, 'min_price': 170.0, 
             'max_price': 180.0, 'avg_volume': 1000000, 'count': 10}
        ]
        mock_aggregate.return_value = mock_agg
        
        mock_data = Mock()
        mock_data.symbol = 'AAPL'
        mock_data.price = 175.5
        mock_latest.return_value = [mock_data]
        
        context = {"token": "viewer_token"}
        result = call_tool("get_market_summary", {"symbols": ["AAPL"]}, context=context)
        
        assert result['isError'] is False
        assert 'AAPL' in result['content'][0]['text']


class TestMCPToolErrorHandlingMocked:
    """Tests for error handling in MCP tools with mocked database"""
    
    @patch('src.mcp.tools.database.get_session')
    def test_unknown_tool(self, mock_get_db):
        """Test calling an unknown tool"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        result = call_tool("unknown_tool", {})
        
        assert result['isError'] is True
        assert 'Unknown tool' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_database_connection_error(self, mock_get_user, mock_get_db):
        """Test handling database connection errors"""
        from sqlalchemy.exc import OperationalError
        mock_get_db.side_effect = OperationalError("Connection failed", None, None)
        
        result = call_tool("query_transactions", {"user_id": 1})
        
        assert result['isError'] is True
        assert 'Database connection failed' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_validation_error(self, mock_get_user, mock_get_db):
        """Test handling validation errors"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_transactions_with_filters') as mock_query:
            mock_query.side_effect = ValidationError("Invalid input", "user_id")
            
            context = {"token": "admin_token"}
            result = call_tool("query_transactions", {"user_id": -1}, context=context)
            
            assert result['isError'] is True
            assert 'Validation error' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_not_found_error(self, mock_get_user, mock_get_db):
        """Test handling NotFoundError"""
        from src.utils.exceptions import NotFoundError
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_portfolio_by_id') as mock_get_portfolio:
            mock_get_portfolio.side_effect = NotFoundError("Portfolio not found", "portfolio_id")
            
            context = {"token": "admin_token"}
            result = call_tool("analyze_risk_metrics", {"portfolio_id": 999}, context=context)
            
            assert result['isError'] is True
            assert 'not found' in result['content'][0]['text'].lower()
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_sqlalchemy_error(self, mock_get_user, mock_get_db):
        """Test handling SQLAlchemyError"""
        from sqlalchemy.exc import SQLAlchemyError
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_transactions_with_filters') as mock_query:
            mock_query.side_effect = SQLAlchemyError("SQL error", None, None)
            
            context = {"token": "admin_token"}
            result = call_tool("query_transactions", {"user_id": 1}, context=context)
            
            assert result['isError'] is True
            assert 'Database error' in result['content'][0]['text'] or 'Database error in tool' in result['content'][0]['text'] or 'SQL error' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_date_format(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid date format"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", {
            "user_id": 1,
            "start_date": "invalid-date"
        }, context=context)
        
        assert result['isError'] is True
        assert 'Invalid start_date format' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_end_date_format(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid end_date format"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", {
            "user_id": 1,
            "end_date": "not-a-date"
        }, context=context)
        
        assert result['isError'] is True
        assert 'Invalid end_date format' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_risk_score_min(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid min_risk_score"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", {
            "user_id": 1,
            "min_risk_score": 1.5  # Invalid: > 1.0
        }, context=context)
        
        assert result['isError'] is True
        assert 'min_risk_score must be between 0.0 and 1.0' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_query_transactions_invalid_risk_score_max(self, mock_get_user, mock_get_db):
        """Test query_transactions with invalid max_risk_score"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        context = {"token": "admin_token"}
        result = call_tool("query_transactions", {
            "user_id": 1,
            "max_risk_score": -0.1  # Invalid: < 0.0
        }, context=context)
        
        assert result['isError'] is True
        assert 'max_risk_score must be between 0.0 and 1.0' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_analyze_risk_metrics_no_period_no_transactions(self, mock_get_user, mock_get_db):
        """Test analyze_risk_metrics with no period and no transactions"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_portfolio_by_id') as mock_get_portfolio:
            mock_portfolio = MagicMock()
            mock_portfolio.id = 1
            mock_portfolio.assets = '{}'
            mock_get_portfolio.return_value = mock_portfolio
            
            with patch('src.mcp.tools.get_portfolio_transaction_history') as mock_get_txns:
                mock_get_txns.return_value = []  # No transactions
                
                with patch('src.mcp.tools.get_latest_prices_dict') as mock_prices:
                    mock_prices.return_value = {}
                    
                    context = {"token": "admin_token"}
                    result = call_tool("analyze_risk_metrics", {
                        "portfolio_id": 1
                        # No period_days specified
                    }, context=context)
                    
                    # With no transactions, RiskAnalyzer returns estimated metrics with warning
                    # The tool should still return a result (not an error)
                    assert result['isError'] is False
                    # Check that the result contains metrics (even if estimated)
                    assert 'content' in result
                    assert len(result['content']) > 0
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_analyze_risk_metrics_error_in_result(self, mock_get_user, mock_get_db):
        """Test analyze_risk_metrics when result contains error"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_portfolio_by_id') as mock_get_portfolio:
            # Create a proper mock portfolio object that can be converted to dict
            from types import SimpleNamespace
            mock_portfolio_obj = SimpleNamespace(id=1, assets='{}')
            mock_get_portfolio.return_value = mock_portfolio_obj
            
            with patch('src.mcp.tools.get_portfolio_transaction_history') as mock_get_txns:
                mock_get_txns.return_value = []
                
                with patch('src.mcp.tools.get_latest_prices_dict') as mock_prices:
                    mock_prices.return_value = {}
                    
                    with patch('src.mcp.tools.RiskAnalyzer') as mock_analyzer:
                        mock_instance = MagicMock()
                        mock_analyzer.return_value = mock_instance
                        mock_instance.calculate_all_metrics.return_value = {"error": "Calculation failed"}
                        
                        context = {"token": "admin_token"}
                        result = call_tool("analyze_risk_metrics", {
                            "portfolio_id": 1,
                            "period_days": 30
                        }, context=context)
                        
                        assert result['isError'] is True
                        assert 'Calculation failed' in result['content'][0]['text']
    
    @patch('src.mcp.tools.database.get_session')
    @patch('src.auth.rbac.get_user_from_context')
    def test_get_market_summary_unexpected_error(self, mock_get_user, mock_get_db):
        """Test get_market_summary with unexpected error"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_user.return_value = {
            "user_id": 1,
            "username": "admin",
            "roles": ["admin"]
        }
        
        with patch('src.mcp.tools.get_latest_market_data') as mock_market:
            mock_market.side_effect = RuntimeError("Unexpected error")
            
            context = {"token": "admin_token"}
            result = call_tool("get_market_summary", {
                "symbols": ["AAPL"]
            }, context=context)
            
            assert result['isError'] is True
            assert 'Unexpected error' in result['content'][0]['text']
    

