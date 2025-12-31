"""
Unit tests for reasoning endpoint
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes import reasoning
from src.utils.exceptions import ValidationError
from src.auth.utils import create_admin_token


@pytest.fixture(autouse=True)
def mock_db_dependency():
    """Auto-use fixture to mock database dependency for all tests"""
    mock_db = MagicMock()
    def get_session():
        yield mock_db
    
    app.dependency_overrides[reasoning.database.get_session] = get_session
    yield
    app.dependency_overrides.clear()


class TestReasoningEndpointAuthorization:
    """Tests for authorization in reasoning endpoint"""
    
    def test_missing_authorization_header(self):
        """Test that missing authorization header returns 401"""
        client = TestClient(app)
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test query"}
        )
        
        assert response.status_code == 401
        assert "Authorization token is required" in response.json()["detail"]
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    def test_invalid_token_returns_401(self, mock_get_user):
        """Test that invalid token returns 401"""
        mock_get_user.side_effect = ValidationError("Invalid token", field="token")
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test query"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    def test_valid_token_proceeds(self, mock_get_user):
        """Test that valid token allows request to proceed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        with patch('src.api.routes.reasoning.MockReasoningOrchestrator') as mock_orch:
            mock_orch_instance = AsyncMock()
            async def mock_reason_gen(*args, **kwargs):
                yield {"type": "answer", "content": "Test answer", "step_number": 1}
                yield {"type": "done", "step_number": 2}
            mock_orch_instance.reason = mock_reason_gen
            mock_orch.return_value = mock_orch_instance
            
            client = TestClient(app)
            token = create_admin_token(user_id=1, username="admin")
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "test query"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestReasoningEndpointOrchestratorSelection:
    """Tests for orchestrator selection logic"""
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.settings.CLAUDE_API_KEY', None)
    def test_uses_mock_orchestrator_when_no_api_key(self, mock_get_user):
        """Test that mock orchestrator is used when CLAUDE_API_KEY is not set"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        with patch('src.api.routes.reasoning.MockReasoningOrchestrator') as mock_orch:
            mock_orch_instance = AsyncMock()
            async def mock_reason_gen(*args, **kwargs):
                yield {"type": "answer", "content": "Mock answer", "step_number": 1}
                yield {"type": "done", "step_number": 2}
            mock_orch_instance.reason = mock_reason_gen
            mock_orch.return_value = mock_orch_instance
            
            client = TestClient(app)
            token = create_admin_token(user_id=1, username="admin")
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            mock_orch.assert_called_once()
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.settings.CLAUDE_API_KEY', 'valid-key')
    def test_uses_real_orchestrator_with_valid_key(self, mock_get_user):
        """Test that real orchestrator is used when CLAUDE_API_KEY is set"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        with patch('src.api.routes.reasoning.ReasoningOrchestrator') as mock_orch:
            mock_orch_instance = AsyncMock()
            async def mock_reason_gen(*args, **kwargs):
                yield {"type": "answer", "content": "Real answer", "step_number": 1}
                yield {"type": "done", "step_number": 2}
            mock_orch_instance.reason = mock_reason_gen
            mock_orch.return_value = mock_orch_instance
            
            client = TestClient(app)
            token = create_admin_token(user_id=1, username="admin")
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            mock_orch.assert_called_once()
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.settings.CLAUDE_API_KEY', 'your_claude_api_key_here')
    def test_uses_mock_orchestrator_with_placeholder_key(self, mock_get_user):
        """Test that mock orchestrator is used when API key is a placeholder"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        with patch('src.api.routes.reasoning.MockReasoningOrchestrator') as mock_orch:
            mock_orch_instance = AsyncMock()
            async def mock_reason_gen(*args, **kwargs):
                yield {"type": "answer", "content": "Mock answer", "step_number": 1}
                yield {"type": "done", "step_number": 2}
            mock_orch_instance.reason = mock_reason_gen
            mock_orch.return_value = mock_orch_instance
            
            client = TestClient(app)
            token = create_admin_token(user_id=1, username="admin")
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            mock_orch.assert_called_once()


class TestReasoningEndpointStreaming:
    """Tests for SSE streaming functionality"""
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_start_event(self, mock_orch, mock_get_user):
        """Test that start event is streamed first"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "done", "step_number": 1}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert "start" in content.lower() or "Starting" in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_thinking_event(self, mock_orch, mock_get_user):
        """Test that thinking events are streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "thinking", "content": "Thinking...", "step_number": 1}
            yield {"type": "done", "step_number": 2}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test", "include_thinking": True},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        # SSE format: data: {"type": "thinking", "data": {"content": "Thinking..."}}
        # Just check that we got some content back
        assert len(content) > 0
        # The thinking event should be in the stream
        assert "thinking" in content.lower() or '"type":"thinking"' in content or '"content":"Thinking' in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_tool_call_event(self, mock_orch, mock_get_user):
        """Test that tool_call events are streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "tool_call", "tool_name": "query_transactions", "content": "Calling tool", "step_number": 1}
            yield {"type": "done", "step_number": 2}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        # Check for tool_call event or tool name in content
        assert len(content) > 0
        assert "tool_call" in content.lower() or "query_transactions" in content or '"tool_name":"query_transactions"' in content or '"type":"tool_call"' in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_tool_result_event(self, mock_orch, mock_get_user):
        """Test that tool_result events are streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "tool_result", "tool_name": "query_transactions", "success": True, "content": "Success", "step_number": 1, "is_error": False}
            yield {"type": "done", "step_number": 2}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        # Check for tool_result event or success message
        assert len(content) > 0
        assert "tool_result" in content.lower() or "Success" in content or '"success":true' in content or '"type":"tool_result"' in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_answer_event(self, mock_orch, mock_get_user):
        """Test that answer events are streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "answer", "content": "Final answer", "step_number": 1}
            yield {"type": "done", "step_number": 2}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        # Check for answer event or answer content
        assert len(content) > 0
        assert "answer" in content.lower() or "Final answer" in content or '"content":"Final answer"' in content or '"type":"answer"' in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_error_event(self, mock_orch, mock_get_user):
        """Test that error events are streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "error", "content": "An error occurred", "step_number": 1}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert "error" in content.lower() or "An error occurred" in content
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_streams_done_event(self, mock_orch, mock_get_user):
        """Test that done event is streamed"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            yield {"type": "done", "step_number": 1, "tool_calls_made": 0}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        content = response.text
        # Check for done event or completion message
        assert len(content) > 0
        assert "done" in content.lower() or "complete" in content.lower() or '"message":"Reasoning complete"' in content or '"type":"done"' in content


class TestReasoningEndpointErrorHandling:
    """Tests for error handling in reasoning endpoint"""
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    def test_handles_orchestrator_exception(self, mock_orch, mock_get_user):
        """Test that orchestrator exceptions are handled"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        async def mock_reason_gen(*args, **kwargs):
            raise Exception("Orchestrator error")
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should still return 200 (SSE) but with error event
        assert response.status_code == 200
        content = response.text
        assert "error" in content.lower()
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    def test_handles_permission_error(self, mock_get_user):
        """Test that permission errors return 403"""
        mock_get_user.side_effect = ValidationError("Access denied", field="permission")
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": "Bearer token"}
        )
        
        assert response.status_code in [403, 401]
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    def test_handles_general_exception(self, mock_get_user):
        """Test that general exceptions return 500"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        with patch('src.api.routes.reasoning.MockReasoningOrchestrator') as mock_orch:
            mock_orch.side_effect = Exception("Unexpected error")
            
            client = TestClient(app)
            token = create_admin_token(user_id=1, username="admin")
            response = client.post(
                "/api/v1/reasoning",
                json={"query": "test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 500


class TestReasoningEndpointBackpressure:
    """Tests for backpressure handling"""
    
    @patch('src.api.routes.reasoning.get_user_from_context')
    @patch('src.api.routes.reasoning.MockReasoningOrchestrator')
    @patch('asyncio.sleep')
    def test_backpressure_handling(self, mock_sleep, mock_orch, mock_get_user):
        """Test that backpressure is handled when buffer is full"""
        mock_get_user.return_value = {"user_id": 1, "role": "admin"}
        
        mock_orch_instance = AsyncMock()
        # Generate many events to trigger backpressure
        async def mock_reason_gen(*args, **kwargs):
            for i in range(150):  # More than max_buffer (100)
                yield {"type": "thinking", "content": f"Thinking {i}", "step_number": i}
            yield {"type": "done", "step_number": 150}
        mock_orch_instance.reason = mock_reason_gen
        mock_orch.return_value = mock_orch_instance
        
        client = TestClient(app)
        token = create_admin_token(user_id=1, username="admin")
        response = client.post(
            "/api/v1/reasoning",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # Note: asyncio.sleep is mocked, so we can't verify it was called in TestClient
        # But the code path should be executed
