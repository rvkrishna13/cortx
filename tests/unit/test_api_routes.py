"""
Unit tests for API routes
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from src.api.main import app
from src.auth.utils import create_admin_token, create_viewer_token, create_analyst_token


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Create admin token"""
    return create_admin_token(user_id=1, username="admin")


@pytest.fixture
def viewer_token():
    """Create viewer token"""
    return create_viewer_token(user_id=5, username="viewer")


class TestReasoningEndpoint:
    """Unit tests for reasoning endpoint - covered by test_reasoning_endpoint.py"""
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_endpoint_success(self, client, admin_token):
        """Test successful reasoning endpoint call"""
        pass
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_endpoint_no_auth(self, client):
        """Test reasoning endpoint without authorization"""
        pass
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_endpoint_invalid_token(self, client):
        """Test reasoning endpoint with invalid token"""
        pass
    
    @pytest.mark.skip(reason="Covered by test_reasoning_endpoint.py")
    def test_reasoning_endpoint_without_thinking(self, client, admin_token):
        """Test reasoning endpoint without thinking"""
        pass


class TestMCPEndpoint:
    """Unit tests for MCP endpoint"""
    
    def test_mcp_endpoint_initialize(self, client, admin_token):
        """Test MCP initialize method"""
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"
    
    def test_mcp_endpoint_no_auth(self, client):
        """Test MCP endpoint without authorization"""
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )
        
        assert response.status_code == 401
        assert "Authorization token is required" in response.json()["detail"]
    
    @patch('src.api.routes.mcp.list_tools')
    def test_mcp_endpoint_list_tools(self, mock_list_tools, client, admin_token):
        """Test MCP tools/list method"""
        mock_list_tools.return_value = [
            {"name": "query_transactions", "description": "Query transactions"}
        ]
        
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
    
    @patch('src.api.routes.mcp.call_tool')
    def test_mcp_endpoint_call_tool_success(self, mock_call_tool, client, admin_token):
        """Test MCP tools/call method success"""
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Result"}],
            "isError": False
        }
        
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_market_summary",
                    "arguments": {}
                }
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    @patch('src.api.routes.mcp.call_tool')
    def test_mcp_endpoint_call_tool_error(self, mock_call_tool, client, admin_token):
        """Test MCP tools/call method with error"""
        mock_call_tool.return_value = {
            "content": [{"type": "text", "text": "Error message"}],
            "isError": True
        }
        
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "query_transactions",
                    "arguments": {}
                }
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    def test_mcp_endpoint_invalid_method(self, client, admin_token):
        """Test MCP endpoint with invalid method"""
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "invalid_method",
                "params": {}
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
    
    def test_mcp_endpoint_invalid_token(self, client):
        """Test MCP endpoint with invalid token"""
        response = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]
    
    @pytest.mark.skip(reason="Covered by test_rbac.py")
    @patch('src.api.routes.mcp.call_tool')
    def test_mcp_endpoint_permission_denied(self, mock_call_tool, client, viewer_token):
        """Test MCP endpoint with permission denied"""
        pass
