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

