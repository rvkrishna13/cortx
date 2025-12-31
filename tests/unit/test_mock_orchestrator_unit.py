"""
Unit tests for MockReasoningOrchestrator
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.services.mock_orchestrator import MockReasoningOrchestrator


class TestMockOrchestratorInit:
    """Tests for MockReasoningOrchestrator initialization"""
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_init(self, mock_list_tools):
        """Test orchestrator initialization"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        assert orchestrator.available_tools == []
        assert orchestrator.request_context is None
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_init_with_context(self, mock_list_tools):
        """Test orchestrator initialization with request context"""
        mock_list_tools.return_value = []
        context = MagicMock()
        orchestrator = MockReasoningOrchestrator(request_context=context)
        
        assert orchestrator.request_context == context


class TestMockOrchestratorQueryParsing:
    """Tests for query parsing methods"""
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_parse_query_to_tools_portfolio(self, mock_list_tools):
        """Test parsing portfolio analysis query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tools = orchestrator._parse_query_to_tools("Analyze portfolio 2", None)
        
        assert len(tools) == 1
        assert tools[0]["name"] == "analyze_risk_metrics"
        assert tools[0]["arguments"]["portfolio_id"] == 2
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_parse_query_to_tools_transactions(self, mock_list_tools):
        """Test parsing transaction query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tools = orchestrator._parse_query_to_tools("Show transactions for user 5", None)
        
        assert len(tools) == 1
        assert tools[0]["name"] == "query_transactions"
        assert tools[0]["arguments"]["user_id"] == 5
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_parse_query_to_tools_market_data(self, mock_list_tools):
        """Test parsing market data query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tools = orchestrator._parse_query_to_tools("Get market summary for AAPL", None)
        
        # The parser may return multiple tools, so check that get_market_summary is in the results
        tool_names = [t["name"] for t in tools]
        assert "get_market_summary" in tool_names
        
        # Find the market summary tool and check its arguments
        market_tool = next((t for t in tools if t["name"] == "get_market_summary"), None)
        assert market_tool is not None
        args = market_tool["arguments"]
        assert "AAPL" in args.get("symbols", []) or args.get("symbol") == "AAPL" or "AAPL" in str(args)
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_parse_query_to_tools_multiple(self, mock_list_tools):
        """Test parsing query with multiple tools"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tools = orchestrator._parse_query_to_tools("Analyze portfolio 1 and show market data", None)
        
        assert len(tools) >= 1
        tool_names = [t["name"] for t in tools]
        assert "analyze_risk_metrics" in tool_names or "get_market_summary" in tool_names


class TestMockOrchestratorExtractArgs:
    """Tests for argument extraction methods"""
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_portfolio_id(self, mock_list_tools):
        """Test extracting portfolio ID from query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        portfolio_id = orchestrator._extract_portfolio_id("Analyze portfolio 5")
        assert portfolio_id == 5
        
        portfolio_id = orchestrator._extract_portfolio_id("Show portfolio 10 metrics")
        assert portfolio_id == 10
        
        portfolio_id = orchestrator._extract_portfolio_id("No portfolio here")
        assert portfolio_id is None
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_period_days(self, mock_list_tools):
        """Test extracting period days from query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        days = orchestrator._extract_period_days("Analyze over 60 days")
        assert days == 60
        
        days = orchestrator._extract_period_days("Last 30 days")
        assert days == 30
        
        days = orchestrator._extract_period_days("No period specified")
        assert days is None


class TestMockOrchestratorFormatting:
    """Tests for formatting methods"""
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_format_tool_result(self, mock_list_tools):
        """Test formatting tool result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tool_result = {
            "content": [{"type": "text", "text": "Result text"}],
            "isError": False
        }
        
        result = orchestrator._format_tool_result(tool_result)
        assert "Result text" in result
        assert "isError" not in result or "Error" not in result
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_generate_thinking_text(self, mock_list_tools):
        """Test generating thinking text"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        text = orchestrator._generate_thinking_text("Analyze portfolio 2")
        assert len(text) > 0
        assert "portfolio" in text.lower() or "analyze" in text.lower()
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_generate_help_message(self, mock_list_tools):
        """Test generating help message"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        message = orchestrator._generate_help_message("Unknown query")
        assert len(message) > 0
        assert "help" in message.lower() or "query" in message.lower()


class TestMockOrchestratorReason:
    """Tests for reason method"""
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_success(self, mock_call_tool, mock_list_tools):
        """Test successful reason call"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        assert any(e.get("type") == "thinking" for e in events)
        assert any(e.get("type") == "done" for e in events)
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_reason_no_tools(self, mock_list_tools):
        """Test reason call with no tools identified"""
        mock_list_tools.return_value = []
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Random query that doesn't match", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        assert any(e.get("type") == "done" for e in events)
        # Should have help message
        final_events = [e for e in events if e.get("type") == "answer"]
        assert len(final_events) > 0
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_tool_error(self, mock_call_tool, mock_list_tools):
        """Test reason call when tool encounters error"""
        mock_list_tools.return_value = []
        mock_call_tool.side_effect = Exception("Tool error")
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        assert any(e.get("type") == "tool_result" and e.get("is_error") for e in events)
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_without_thinking(self, mock_call_tool, mock_list_tools):
        """Test reason call without thinking steps"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}, include_thinking=False):
            events.append(event)
        
        assert len(events) > 0
        # Should not have thinking events
        thinking_events = [e for e in events if e.get("type") == "thinking"]
        assert len(thinking_events) == 0
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_user_id(self, mock_call_tool, mock_list_tools):
        """Test reason call with user_id parameter"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Show transactions", user_id=5, auth_context={}):
            events.append(event)
        
        assert len(events) > 0
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_request_context(self, mock_call_tool, mock_list_tools):
        """Test reason call with request context for metrics"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        mock_context = MagicMock()
        mock_context.record_tool_call = MagicMock()
        mock_context.request_id = "test-123"
        
        orchestrator = MockReasoningOrchestrator(request_context=mock_context)
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        # Verify tool calls were recorded
        assert mock_context.record_tool_call.called
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_tool_chaining(self, mock_call_tool, mock_list_tools):
        """Test reason call with tool chaining"""
        mock_list_tools.return_value = []
        # First call returns portfolio data, second call returns market data
        mock_call_tool.side_effect = [
            {
                "content": [{"type": "text", "text": "Portfolio 1 Risk Analysis:\nPortfolio ID: 1"}],
                "isError": False
            },
            {
                "content": [{"type": "text", "text": "AAPL: $150.00"}],
                "isError": False
            }
        ]
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 1 and show market data", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        # Should have multiple tool calls
        tool_call_events = [e for e in events if e.get("type") == "tool_call"]
        assert len(tool_call_events) >= 1
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_reason_exception_handling(self, mock_list_tools):
        """Test reason call exception handling"""
        mock_list_tools.return_value = []
        
        orchestrator = MockReasoningOrchestrator()
        
        # Force an exception in the reason method
        with patch.object(orchestrator, '_parse_query_to_tools', side_effect=Exception("Parse error")):
            events = []
            async for event in orchestrator.reason("Test query", auth_context={}):
                events.append(event)
            
            assert len(events) > 0
            # Should have error handling
            assert any(e.get("type") in ["error", "answer", "done"] for e in events)
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_reason_max_turns_reached(self, mock_list_tools):
        """Test reason call when max turns is reached"""
        mock_list_tools.return_value = []
        
        orchestrator = MockReasoningOrchestrator()
        
        # Mock to always return tools to call (infinite loop scenario)
        with patch.object(orchestrator, '_parse_query_to_tools', return_value=[{"name": "query_transactions", "arguments": {"user_id": 1}}]):
            with patch('src.services.mock_orchestrator.call_tool', return_value={"content": [{"type": "text", "text": "Result"}], "isError": False}):
                with patch.object(orchestrator, '_determine_chained_tools', return_value=[{"name": "query_transactions", "arguments": {"user_id": 1}}]):
                    events = []
                    async for event in orchestrator.reason("Test query", auth_context={}):
                        events.append(event)
                        # Break after reasonable number of events to avoid infinite loop
                        if len(events) > 100:
                            break
                    
                    assert len(events) > 0
                    # Should eventually complete
                    assert any(e.get("type") == "done" for e in events)
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_transaction_args(self, mock_list_tools):
        """Test extracting transaction arguments from query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        # Test user ID extraction
        args = orchestrator._extract_transaction_args("Show transactions for user 5")
        assert args.get("user_id") == 5
        
        # Test date ranges
        args = orchestrator._extract_transaction_args("Show transactions from yesterday")
        assert "start_date" in args
        
        args = orchestrator._extract_transaction_args("Show transactions from last week")
        assert "start_date" in args
        assert "end_date" in args
        
        # Test amount ranges
        args = orchestrator._extract_transaction_args("Show transactions over $1000")
        assert args.get("min_amount") == 1000.0
        
        args = orchestrator._extract_transaction_args("Show transactions under $500")
        assert args.get("max_amount") == 500.0
        
        # Test risk keywords
        args = orchestrator._extract_transaction_args("Show high risk transactions")
        assert args.get("min_risk_score") == 0.7
        
        args = orchestrator._extract_transaction_args("Show low risk transactions")
        assert args.get("max_risk_score") == 0.3
        
        # Test category
        args = orchestrator._extract_transaction_args("Show groceries transactions")
        assert args.get("category") == "groceries"
        
        # Test limit
        args = orchestrator._extract_transaction_args("Show recent 5 transactions")
        assert args.get("limit") == 5
        
        args = orchestrator._extract_transaction_args("Show 10 transactions")
        assert args.get("limit") == 10
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_market_args(self, mock_list_tools):
        """Test extracting market summary arguments from query"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        # Test symbol extraction
        args = orchestrator._extract_market_args("Get market summary for AAPL")
        assert "AAPL" in args.get("symbols", [])
        
        args = orchestrator._extract_market_args("Show me GOOGL and TSLA prices")
        symbols = args.get("symbols", [])
        assert "GOOGL" in symbols or "TSLA" in symbols
        
        # Test period extraction
        args = orchestrator._extract_market_args("Get market data for AAPL by hour")
        assert args.get("period") == "hour"
        
        args = orchestrator._extract_market_args("Get market data for AAPL by week")
        assert args.get("period") == "week"
        
        args = orchestrator._extract_market_args("Get market data for AAPL")
        assert args.get("period") == "day"  # Default
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_data_from_results(self, mock_list_tools):
        """Test extracting data from tool results"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        # Test with portfolio results
        results = [{
            "tool_name": "analyze_risk_metrics",
            "result": "Portfolio 1 Risk Analysis:",
            "is_error": False
        }]
        
        with patch.object(orchestrator, '_extract_symbols_from_portfolio_result', return_value=["AAPL", "GOOGL"]):
            extracted = orchestrator._extract_data_from_results(results)
            assert "portfolio_symbols" in extracted
            assert len(extracted["portfolio_symbols"]) == 2
        
        # Test with transaction results
        results = [{
            "tool_name": "query_transactions",
            "result": "User: 5\nTransaction ID: 1",
            "is_error": False
        }]
        
        with patch.object(orchestrator, '_extract_user_ids_from_transactions', return_value=[5]):
            extracted = orchestrator._extract_data_from_results(results)
            assert "transaction_user_ids" in extracted
            assert 5 in extracted["transaction_user_ids"]
        
        # Test with market results
        results = [{
            "tool_name": "get_market_summary",
            "result": "AAPL:\n  Price: $150.00",
            "is_error": False
        }]
        
        with patch.object(orchestrator, '_extract_symbols_from_market_result', return_value=["AAPL"]):
            extracted = orchestrator._extract_data_from_results(results)
            assert "market_symbols" in extracted
            assert "AAPL" in extracted["market_symbols"]
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_symbols_from_portfolio_result(self, mock_list_tools):
        """Test extracting symbols from portfolio result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        # Test with portfolio ID in result
        result_text = "Portfolio 1 Risk Analysis:"
        
        with patch('src.database.queries.get_portfolio_by_id') as mock_get_portfolio:
            mock_portfolio = MagicMock()
            mock_portfolio.assets = '{"AAPL": 100, "GOOGL": 50}'
            mock_get_portfolio.return_value = mock_portfolio
            
            with patch('src.database.connection.database') as mock_db:
                mock_session = MagicMock()
                mock_db.get_session.return_value = mock_session
                mock_session.close = MagicMock()
                
                symbols = orchestrator._extract_symbols_from_portfolio_result(result_text)
                assert len(symbols) == 2
                assert "AAPL" in symbols
                assert "GOOGL" in symbols
        
        # Test with no portfolio ID
        symbols = orchestrator._extract_symbols_from_portfolio_result("No portfolio here")
        assert len(symbols) == 0
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_user_ids_from_transactions(self, mock_list_tools):
        """Test extracting user IDs from transaction result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result_text = "User: 5\nTransaction ID: 1\nUser: 7\nTransaction ID: 2"
        user_ids = orchestrator._extract_user_ids_from_transactions(result_text)
        
        assert len(user_ids) == 2
        assert 5 in user_ids
        assert 7 in user_ids
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_extract_symbols_from_market_result(self, mock_list_tools):
        """Test extracting symbols from market result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result_text = "AAPL:\n  Price: $150.00\nGOOGL:\n  Price: $200.00"
        symbols = orchestrator._extract_symbols_from_market_result(result_text)
        
        assert len(symbols) == 2
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_determine_chained_tools(self, mock_list_tools):
        """Test determining chained tools"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        # Test with portfolio results and market query
        current_results = [{
            "tool_name": "analyze_risk_metrics",
            "result": "Portfolio 1 Risk Analysis:",
            "is_error": False
        }]
        
        all_results = current_results.copy()
        
        with patch.object(orchestrator, '_extract_data_from_results', return_value={"portfolio_symbols": ["AAPL", "GOOGL"]}):
            next_tools = orchestrator._determine_chained_tools("Show market data", current_results, all_results)
            assert len(next_tools) > 0
            assert next_tools[0]["name"] == "get_market_summary"
            assert "AAPL" in next_tools[0]["arguments"]["symbols"]
        
        # Test when market data already exists
        all_results.append({
            "tool_name": "get_market_summary",
            "arguments": {"symbols": ["AAPL", "GOOGL"]},
            "is_error": False
        })
        
        with patch.object(orchestrator, '_extract_data_from_results', return_value={"portfolio_symbols": ["AAPL", "GOOGL"]}):
            next_tools = orchestrator._determine_chained_tools("Show market data", current_results, all_results)
            assert len(next_tools) == 0  # Already have market data
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_format_tool_result_error(self, mock_list_tools):
        """Test formatting tool result with error"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tool_result = {
            "content": [{"type": "text", "text": "Error occurred"}],
            "isError": True
        }
        
        result = orchestrator._format_tool_result(tool_result)
        assert "Error occurred" in result
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_format_tool_result_no_content(self, mock_list_tools):
        """Test formatting tool result with no content"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tool_result = {
            "content": [],
            "isError": False
        }
        
        result = orchestrator._format_tool_result(tool_result)
        assert result == "No results"
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_generate_final_answer(self, mock_list_tools):
        """Test generating final answer"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tool_results = [{
            "tool_name": "query_transactions",
            "result": "Transaction ID: 1, User: 5, Amount: 100.0",
            "is_error": False
        }]
        
        answer = orchestrator._generate_final_answer("Show transactions", tool_results)
        assert "query_transactions" in answer
        assert "status" in answer
        assert "tools_called" in answer
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_generate_final_answer_with_errors(self, mock_list_tools):
        """Test generating final answer with errors"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        tool_results = [{
            "tool_name": "query_transactions",
            "result": "Error occurred",
            "is_error": True
        }]
        
        answer = orchestrator._generate_final_answer("Show transactions", tool_results)
        assert "error" in answer.lower() or "status" in answer
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_get_status_message(self, mock_list_tools):
        """Test getting status message"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        message = orchestrator._get_status_message(True, False, 2)
        assert "complete" in message.lower()
        
        message = orchestrator._get_status_message(True, True, 2)
        assert "error" in message.lower()
        
        message = orchestrator._get_status_message(False, True, 2)
        assert "unable" in message.lower() or "error" in message.lower()
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_summarize_tool_result_transactions(self, mock_list_tools):
        """Test summarizing transaction tool result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result = "Transaction ID: 1, User: 5\nTransaction ID: 2, User: 5\nTransaction ID: 3, User: 5"
        summary = orchestrator._summarize_tool_result("query_transactions", result)
        assert "3 transaction" in summary.lower()
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_summarize_tool_result_market_data(self, mock_list_tools):
        """Test summarizing market data tool result"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result = "AAPL:\n  Price: $150.00\nGOOGL:\n  Price: $200.00\nTSLA:\n  Price: $300.00"
        summary = orchestrator._summarize_tool_result("get_market_summary", result)
        assert "market data" in summary.lower() or "symbol" in summary.lower()
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_summarize_tool_result_structured_transactions(self, mock_list_tools):
        """Test summarizing transaction tool result in structured format"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result = "Transaction ID: 1, User: 5, Amount: 100.0 USD"
        summary = orchestrator._summarize_tool_result_structured("query_transactions", result)
        assert summary["type"] == "transactions"
        assert "count" in summary
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_summarize_tool_result_structured_risk_metrics(self, mock_list_tools):
        """Test summarizing risk metrics tool result in structured format"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result = "Portfolio 1 Risk Analysis:\nVolatility: 0.15\nSharpe Ratio: 1.2"
        summary = orchestrator._summarize_tool_result_structured("analyze_risk_metrics", result)
        assert summary["type"] == "risk_metrics"
        assert "metrics" in summary
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_summarize_tool_result_structured_market_data(self, mock_list_tools):
        """Test summarizing market data tool result in structured format"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        result = "AAPL:\n  Price: $150.00\nGOOGL:\n  Price: $200.00"
        summary = orchestrator._summarize_tool_result_structured("get_market_summary", result)
        assert summary["type"] == "market_data"
        assert "symbol_count" in summary
    
    @patch('src.services.mock_orchestrator.list_tools')
    def test_chunk_text(self, mock_list_tools):
        """Test chunking text for streaming"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        text = "This is a long text that needs to be chunked"
        chunks = orchestrator._chunk_text(text, chunk_size=10)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 10 for chunk in chunks)
        assert "".join(chunks) == text
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_async_sleep(self, mock_list_tools):
        """Test async sleep helper"""
        mock_list_tools.return_value = []
        orchestrator = MockReasoningOrchestrator()
        
        import time
        start = time.time()
        await orchestrator._async_sleep(0.1)
        elapsed = time.time() - start
        
        assert elapsed >= 0.1

    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_tool_error(self, mock_call_tool, mock_list_tools):
        """Test reason call when tool encounters error"""
        mock_list_tools.return_value = []
        mock_call_tool.side_effect = Exception("Tool error")
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        assert any(e.get("type") == "tool_result" and e.get("is_error") for e in events)
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_without_thinking(self, mock_call_tool, mock_list_tools):
        """Test reason call without thinking steps"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}, include_thinking=False):
            events.append(event)
        
        assert len(events) > 0
        # Should not have thinking events
        thinking_events = [e for e in events if e.get("type") == "thinking"]
        assert len(thinking_events) == 0
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_user_id(self, mock_call_tool, mock_list_tools):
        """Test reason call with user_id parameter"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Show transactions", user_id=5, auth_context={}):
            events.append(event)
        
        assert len(events) > 0
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_with_request_context(self, mock_call_tool, mock_list_tools):
        """Test reason call with request context for metrics"""
        mock_list_tools.return_value = []
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        mock_context = MagicMock()
        mock_context.record_tool_call = MagicMock()
        mock_context.request_id = "test-123"
        
        orchestrator = MockReasoningOrchestrator(request_context=mock_context)
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 2", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        # Verify tool calls were recorded
        assert mock_context.record_tool_call.called
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    @patch('src.services.mock_orchestrator.call_tool')
    async def test_reason_tool_chaining(self, mock_call_tool, mock_list_tools):
        """Test reason call with tool chaining"""
        mock_list_tools.return_value = []
        # First call returns portfolio data, second call returns market data
        mock_call_tool.side_effect = [
            {
                "content": [{"type": "text", "text": "Portfolio 1 Risk Analysis:\nPortfolio ID: 1"}],
                "isError": False
            },
            {
                "content": [{"type": "text", "text": "AAPL: $150.00"}],
                "isError": False
            }
        ]
        
        orchestrator = MockReasoningOrchestrator()
        
        events = []
        async for event in orchestrator.reason("Analyze portfolio 1 and show market data", auth_context={}):
            events.append(event)
        
        assert len(events) > 0
        # Should have multiple tool calls
        tool_call_events = [e for e in events if e.get("type") == "tool_call"]
        assert len(tool_call_events) >= 1
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_reason_exception_handling(self, mock_list_tools):
        """Test reason call exception handling"""
        mock_list_tools.return_value = []
        
        orchestrator = MockReasoningOrchestrator()
        
        # Force an exception in the reason method
        with patch.object(orchestrator, '_parse_query_to_tools', side_effect=Exception("Parse error")):
            events = []
            async for event in orchestrator.reason("Test query", auth_context={}):
                events.append(event)
            
            assert len(events) > 0
            # Should have error handling
            assert any(e.get("type") in ["error", "answer", "done"] for e in events)
    
    @pytest.mark.asyncio
    @patch('src.services.mock_orchestrator.list_tools')
    async def test_reason_max_turns_reached(self, mock_list_tools):
        """Test reason call when max turns is reached"""
        mock_list_tools.return_value = []
        
        orchestrator = MockReasoningOrchestrator()
        
        # Mock to always return tools to call (infinite loop scenario)
        with patch.object(orchestrator, '_parse_query_to_tools', return_value=[{"name": "query_transactions", "arguments": {"user_id": 1}}]):
            with patch('src.services.mock_orchestrator.call_tool', return_value={"content": [{"type": "text", "text": "Result"}], "isError": False}):
                with patch.object(orchestrator, '_determine_chained_tools', return_value=[{"name": "query_transactions", "arguments": {"user_id": 1}}]):
                    events = []
                    async for event in orchestrator.reason("Test query", auth_context={}):
                        events.append(event)
                        # Break after reasonable number of events to avoid infinite loop
                        if len(events) > 100:
                            break
                    
                    assert len(events) > 0
                    # Should eventually complete
                    assert any(e.get("type") == "done" for e in events)

