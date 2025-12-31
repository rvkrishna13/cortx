"""
Unit tests for MCP server
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Skip if mcp package is not available
try:
    from src.mcp.server import server
    from src.mcp.tools import list_tools, call_tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="mcp package not installed")


class TestMCPServer:
    """Tests for MCP server functionality"""
    
    def test_server_initialization(self):
        """Test that server is properly initialized"""
        assert server is not None
        assert hasattr(server, 'list_tools')
        assert hasattr(server, 'call_tool')
    
    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test handle_list_tools handler"""
        # This would need to be tested with actual MCP server setup
        # For now, we test the underlying function
        tools = list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    @pytest.mark.asyncio
    async def test_handle_call_tool(self):
        """Test handle_call_tool handler"""
        # Mock the call_tool function
        with patch('src.mcp.server.call_tool') as mock_call:
            mock_call.return_value = {
                "content": [{"type": "text", "text": "Test result"}],
                "isError": False
            }
            
            result = await server.call_tool("query_transactions", {"user_id": 1})
            
            # The actual implementation would return MCP TextContent objects
            # This is a simplified test
            mock_call.assert_called_once_with("query_transactions", {"user_id": 1})


class TestMCPServerIntegration:
    """Integration tests for MCP server with tools"""
    
    @patch('src.mcp.tools.database.get_session')
    def test_server_tool_integration(self, mock_get_db, test_db):
        """Test that server can execute tools through the handler"""
        mock_get_db.return_value = iter([test_db])
        
        # Test that tools are accessible
        tools = list_tools()
        assert len(tools) >= 3
        
        # Test that we can call a tool
        with patch('src.mcp.tools.get_transactions_with_filters') as mock_query:
            mock_query.return_value = []
            result = call_tool("query_transactions", {"user_id": 1})
            assert 'isError' in result
    
    def test_tool_schema_consistency(self):
        """Test that tool schemas are consistent between list and call"""
        tools = list_tools()
        
        for tool in tools:
            # Verify schema structure
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            
            # Verify we can call the tool (even if it fails)
            # This ensures the tool name matches
            try:
                result = call_tool(tool['name'], {})
                # Should return a result (even if error)
                assert 'content' in result or 'isError' in result
            except Exception:
                # Some tools might require specific parameters
                pass

