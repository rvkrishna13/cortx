"""
Integration tests for streaming reasoning flow
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from src.api.main import app
from src.auth.utils import create_viewer_token, create_analyst_token, create_admin_token


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Create admin token"""
    return create_admin_token(user_id=1, username="admin")


@pytest.fixture
def analyst_token():
    """Create analyst token"""
    return create_analyst_token(user_id=2, username="analyst")


@pytest.fixture
def viewer_token():
    """Create viewer token"""
    return create_viewer_token(user_id=5, username="viewer")


class TestReasoningFlowIntegration:
    """Integration tests for reasoning endpoint flow"""
    
    
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_success(self, mock_orchestrator_class, client, admin_token):
        """Test successful reasoning flow"""
        # Mock database session
        mock_db = MagicMock()
        def get_session():
            yield mock_db
        from src.api.routes import reasoning
        from src.api.main import app
        app.dependency_overrides[reasoning.database.get_session] = get_session
        
        try:
            # Mock orchestrator
            mock_orchestrator = AsyncMock()
            async def mock_reason_gen(*args, **kwargs):
                yield {"type": "thinking", "content": "Analyzing query...", "step_number": 1}
                yield {"type": "tool_call", "tool_name": "get_market_summary", "content": "Calling tool", "step_number": 2}
                yield {"type": "tool_result", "tool_name": "get_market_summary", "success": True, "is_error": False, "content": "Tool completed", "step_number": 3}
                yield {"type": "answer", "content": "Market summary: AAPL is trading at $175.50", "step_number": 4}
                yield {"type": "done", "final_answer": "Market summary: AAPL is trading at $175.50", "tool_calls_made": 1, "step_number": 5}
            
            mock_orchestrator.reason = mock_reason_gen_gen
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Make request
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "Get market summary for AAPL", "include_thinking": True},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        finally:
            app.dependency_overrides.clear()
        
        # Parse SSE events
        content = response.text
        assert "data: " in content
        assert "start" in content
        assert "thinking" in content
        assert "tool_call" in content
        assert "tool_result" in content
        assert "answer" in content
        assert "done" in content
    
    
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_with_multiple_tools(self, mock_orchestrator_class, client, admin_token):
        """Test reasoning flow with multiple tool calls"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_orchestrator = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "tool_call", "tool_name": "query_transactions", "content": "Calling tool 1", "step_number": 2}
            yield {"type": "tool_result", "tool_name": "query_transactions", "success": True, "is_error": False, "content": "Done", "step_number": 3}
            yield {"type": "tool_call", "tool_name": "get_market_summary", "content": "Calling tool 2", "step_number": 4}
            yield {"type": "tool_result", "tool_name": "get_market_summary", "success": True, "is_error": False, "content": "Done", "step_number": 5}
            yield {"type": "answer", "content": "Found 5 transactions and market data", "step_number": 6}
            yield {"type": "done", "final_answer": "Found 5 transactions and market data", "tool_calls_made": 2, "step_number": 7}
        
        mock_orchestrator.reason = mock_reason_gen
        mock_orchestrator_class.return_value = mock_orchestrator
        
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "Show transactions and market data", "include_thinking": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert content.count("tool_call") == 2
        assert content.count("tool_result") == 2
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_no_authorization(self, client):
        """Test reasoning flow without authorization token"""
        pass
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_invalid_token(self, client):
        """Test reasoning flow with invalid token"""
        pass
    
    
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_viewer_permission_denied(self, mock_orchestrator_class, client, viewer_token):
        """Test reasoning flow with viewer role trying to access restricted tool"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_orchestrator = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "tool_call", "tool_name": "query_transactions", "content": "Calling tool", "step_number": 2}
            yield {"type": "tool_result", "tool_name": "query_transactions", "success": False, "is_error": True, "content": "Validation error in tool 'query_transactions': Missing required permissions: ['read:transactions', 'read:user_transactions']", "step_number": 3}
            yield {"type": "answer", "content": "Error: Missing required permissions", "step_number": 4}
            yield {"type": "done", "final_answer": "Error: Missing required permissions", "tool_calls_made": 1, "step_number": 5}
        
        mock_orchestrator.reason = mock_reason_gen
        mock_orchestrator_class.return_value = mock_orchestrator
        
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "Show transactions for user 1", "include_thinking": True},
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 200  # SSE returns 200, error in content
        content = response.text
        assert "Missing required permissions" in content
    
    
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_viewer_can_access_market_data(self, mock_orchestrator_class, client, viewer_token):
        """Test reasoning flow with viewer role accessing allowed tool"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_orchestrator = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "tool_call", "tool_name": "get_market_summary", "content": "Calling tool", "step_number": 2}
            yield {"type": "tool_result", "tool_name": "get_market_summary", "success": True, "is_error": False, "content": "Done", "step_number": 3}
            yield {"type": "answer", "content": "Market data retrieved", "step_number": 4}
            yield {"type": "done", "final_answer": "Market data retrieved", "tool_calls_made": 1, "step_number": 5}
        
        mock_orchestrator.reason = mock_reason_gen
        mock_orchestrator_class.return_value = mock_orchestrator
        
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "Get market summary for AAPL", "include_thinking": True},
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert "get_market_summary" in content
        assert "Market data retrieved" in content
    
    
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_flow_error_handling(self, mock_orchestrator_class, client, admin_token):
        """Test reasoning flow error handling"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_orchestrator = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "thinking", "content": "Analyzing...", "step_number": 1}
            yield {"type": "error", "content": "Database connection failed", "step_number": 2}
        
        mock_orchestrator.reason = mock_reason_gen
        mock_orchestrator_class.return_value = mock_orchestrator
        
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "Get data", "include_thinking": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert "error" in content
        assert "Database connection failed" in content

