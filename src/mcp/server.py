"""
MCP Server Entry Point
This file initializes the MCP server and registers tool handlers.
It runs as a subprocess and communicates with Claude via stdin/stdout.

To run: python -m src.mcp.server
Or: python src/mcp/server.py
"""

import asyncio
import sys
import mcp.server.stdio
from mcp.server import Server

# Import tool handlers from tools.py
from src.mcp.tools import list_tools, call_tool


# Create MCP server instance
# The name identifies this server in Claude's configuration
server = Server("financial-mcp-server")


@server.list_tools()
async def handle_list_tools():
    """
    Handler that tells Claude what tools are available.
    
    This is called when Claude needs to know what capabilities
    this MCP server provides.
    
    Returns:
        List of Tool objects describing available tools
    """
    tools = list_tools()
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """
    Handler that executes a specific tool.
    
    This is called when Claude wants to use one of the available tools.
    The tool name and arguments are provided by Claude.
    
    Args:
        name: The name of the tool to execute (e.g., "query_transactions")
        arguments: Dictionary of arguments Claude is passing to the tool
    
    Returns:
        List of TextContent objects containing the tool's response
    """
    result = await call_tool(name, arguments)
    return result


async def main():
    """
    Main entry point for the MCP server.
    
    This function:
    1. Sets up stdio communication channels
    2. Starts the MCP server
    3. Runs until Claude terminates the process
    
    The server communicates with Claude via stdin/stdout using the MCP protocol.
    """
    try:
        # Create stdio server for communication with Claude
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            # Initialize and run the server
            init_options = server.create_initialization_options()
            
            await server.run(
                read_stream,
                write_stream,
                init_options
            )
    
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        print("Server shutting down...", file=sys.stderr)
    
    except Exception as e:
        # Log any unexpected errors
        print(f"Server error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    """
    Entry point when running the server directly.
    
    Usage:
        python src/mcp/server.py
        
    Or as a module:
        python -m src.mcp.server
    
    Claude Desktop will spawn this as a subprocess based on the
    configuration in claude_desktop_config.json
    """
    # Run the async main function
    asyncio.run(main())