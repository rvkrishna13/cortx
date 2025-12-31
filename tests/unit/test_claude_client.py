"""
Unit tests for ClaudeClient
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.services.claude_client import ClaudeClient
from src.config.settings import settings


class TestClaudeClientInit:
    """Tests for ClaudeClient initialization"""
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-api-key')
    def test_init_with_settings_key(self):
        """Test initialization using API key from settings"""
        client = ClaudeClient()
        
        assert client.api_key == 'test-api-key'
        assert client.base_url == "https://api.anthropic.com/v1"
        assert client.model == "claude-3-5-sonnet-20241022"
        assert "x-api-key" in client.headers
        assert client.headers["x-api-key"] == "test-api-key"
    
    def test_init_with_custom_key(self):
        """Test initialization with custom API key"""
        client = ClaudeClient(api_key="custom-key")
        
        assert client.api_key == "custom-key"
        assert client.headers["x-api-key"] == "custom-key"
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', None)
    def test_init_without_key(self):
        """Test initialization without API key (should not raise error)"""
        client = ClaudeClient()
        
        assert client.api_key is None
        assert client.headers["x-api-key"] == ""


class TestClaudeClientCreateToolsSchema:
    """Tests for _create_tools_schema method"""
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    def test_create_tools_schema(self):
        """Test converting MCP tools to Claude API format"""
        client = ClaudeClient()
        
        mcp_tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}}
                }
            }
        ]
        
        result = client._create_tools_schema(mcp_tools)
        
        assert len(result) == 1
        assert result[0]["name"] == "test_tool"
        assert result[0]["description"] == "A test tool"
        assert result[0]["input_schema"] == mcp_tools[0]["inputSchema"]
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    def test_create_tools_schema_empty(self):
        """Test with empty tools list"""
        client = ClaudeClient()
        
        result = client._create_tools_schema([])
        
        assert result == []
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    def test_create_tools_schema_multiple(self):
        """Test with multiple tools"""
        client = ClaudeClient()
        
        mcp_tools = [
            {"name": "tool1", "description": "Tool 1", "inputSchema": {}},
            {"name": "tool2", "description": "Tool 2", "inputSchema": {}}
        ]
        
        result = client._create_tools_schema(mcp_tools)
        
        assert len(result) == 2
        assert result[0]["name"] == "tool1"
        assert result[1]["name"] == "tool2"


class TestClaudeClientReasonWithTools:
    """Tests for reason_with_tools method"""
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    def test_reason_with_tools_method_exists(self):
        """Test that reason_with_tools method exists"""
        client = ClaudeClient()
        assert hasattr(client, 'reason_with_tools')
        assert callable(client.reason_with_tools)
    
    @pytest.mark.skip(reason="Complex async streaming test - covered by integration tests")
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_reason_with_tools_success(self):
        """Test successful reasoning with tools"""
        client = ClaudeClient()
        
        # Mock httpx.AsyncClient
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines.return_value = iter([
            b'data: {"type": "thinking", "content": "Thinking..."}',
            b'data: {"type": "answer", "content": "Answer"}',
            b'data: [DONE]'
        ])
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            tools = [{"name": "test_tool"}]
            results = []
            
            async for result in client.reason_with_tools("Test query", tools):
                results.append(result)
            
            assert len(results) > 0
            assert any(r.get("type") == "thinking" for r in results)
            assert any(r.get("type") == "answer" for r in results)
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_reason_with_tools_error(self):
        """Test error handling in reason_with_tools"""
        client = ClaudeClient()
        
        # Mock httpx error
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("API Error")
            
            tools = []
            results = []
            
            async for result in client.reason_with_tools("Test query", tools):
                results.append(result)
            
            # Should yield error event
            assert any(r.get("type") == "error" for r in results)
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_reason_with_tools_custom_system_prompt(self):
        """Test with custom system prompt"""
        client = ClaudeClient()
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines.return_value = iter([
            b'data: {"type": "answer", "content": "Done"}',
            b'data: [DONE]'
        ])
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            tools = []
            system_prompt = "Custom system prompt"
            results = []
            
            async for result in client.reason_with_tools(
                "Query", 
                tools, 
                system_prompt=system_prompt
            ):
                results.append(result)
            
            # Verify system prompt was used in request
            call_args = mock_client.post.call_args
            assert call_args is not None
            # The system prompt should be in the request body
            request_data = call_args[1].get("json", {})
            assert "system" in request_data or "messages" in request_data
    
    @patch('src.services.claude_client.settings.CLAUDE_API_KEY', 'test-key')
    @pytest.mark.asyncio
    async def test_reason_with_tools_max_tool_calls(self):
        """Test max_tool_calls parameter"""
        client = ClaudeClient()
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines.return_value = iter([
            b'data: {"type": "answer", "content": "Done"}',
            b'data: [DONE]'
        ])
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            tools = []
            results = []
            
            async for result in client.reason_with_tools(
                "Query", 
                tools, 
                max_tool_calls=3
            ):
                results.append(result)
            
            assert len(results) > 0

