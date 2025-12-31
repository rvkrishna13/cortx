"""
MCP Server HTTP endpoint for Claude Desktop
Implements MCP protocol over HTTP using JSON-RPC 2.0
"""
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import json
import time
from src.mcp.tools import list_tools, call_tool
from src.observability.logging import generate_request_id, set_request_id, get_logger
from src.observability.tracing import RequestContext
from src.observability.metrics import get_metrics_collector
from src.utils.exceptions import ValidationError

router = APIRouter()
logger = get_logger(__name__)
metrics_collector = get_metrics_collector()


async def handle_mcp_request(request: Request, authorization: Optional[str] = None) -> JSONResponse:
    """
    Shared MCP request handler - can be used by both / and /api/v1/mcp endpoints
    """
    request_start_time = time.time()
    request_id = generate_request_id()
    set_request_id(request_id)
    
    try:
        # Authorization is required - reject if not provided
        if not authorization:
            request_duration_ms = (time.time() - request_start_time) * 1000
            metrics_collector.record_endpoint_request(
                endpoint="/api/v1/mcp",
                method="POST",
                duration_ms=request_duration_ms,
                status_code=401,
                request_id=request_id
            )
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Authorization token is required"
            )
        
        # Parse MCP protocol message
        body = await request.json()
        method = body.get("method")
        message_id = body.get("id")
        params = body.get("params", {})
        
        # Extract auth context - authorization is required at this point
        # Handle both "Bearer token" and just "token" formats
        token = authorization
        if token.startswith("Bearer "):
            token = token[7:]
        auth_context = {"token": token}
        
        # Validate token early for non-initialize methods
        if method != "initialize":
            from src.auth.rbac import get_user_from_context
            try:
                user_info = get_user_from_context(auth_context)
            except ValidationError as e:
                request_duration_ms = (time.time() - request_start_time) * 1000
                metrics_collector.record_endpoint_request(
                    endpoint="/api/v1/mcp",
                    method="POST",
                    duration_ms=request_duration_ms,
                    status_code=401,
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized: Invalid or expired token"
                )
        
        # Handle different MCP methods
        if method == "initialize":
            # Server initialization - no auth required for protocol handshake
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "financial-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }
            return JSONResponse(content=response)
        
        elif method == "tools/list":
            # List available tools
            tools = list_tools()
            response = {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": tools
                }
            }
            return JSONResponse(content=response)
        
        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            
            if not tool_name:
                return JSONResponse(
                    status_code=200,  # JSON-RPC uses 200 even for errors
                    content={
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32602,
                            "message": "Invalid params: tool name is required"
                        }
                    }
                )
            
            # Execute tool with timing
            start_time = time.time()
            with RequestContext(request_id) as ctx:
                try:
                    result = call_tool(
                        name=tool_name,
                        arguments=tool_arguments,
                        context=auth_context
                    )
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Record tool call
                    ctx.record_tool_call(
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        success=not result.get("isError", False)
                    )
                    
                    # Format response according to MCP protocol
                    # MCP expects content as list of TextContent objects
                    content = []
                    if result.get("isError"):
                        error_text = ""
                        if result.get("content"):
                            error_text = result["content"][0].get("text", "Unknown error") if result["content"] else "Unknown error"
                        content.append({"type": "text", "text": error_text})
                        
                        # Check if it's a permission/auth error - return proper HTTP status
                        error_lower = error_text.lower()
                        if "missing required permissions" in error_lower or "access denied" in error_lower:
                            # Permission error - return 403
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "jsonrpc": "2.0",
                                    "id": message_id,
                                    "error": {
                                        "code": -32001,
                                        "message": "Forbidden: Insufficient permissions",
                                        "data": error_text
                                    }
                                }
                            )
                    else:
                        for item in result.get("content", []):
                            if item.get("type") == "text":
                                content.append({"type": "text", "text": item.get("text", "")})
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": {
                            "content": content,
                            "isError": result.get("isError", False)
                        }
                    }
                    return JSONResponse(content=response)
                
                except ValidationError as e:
                    # Check if it's a permission error
                    error_msg = str(e)
                    if "permission" in error_msg.lower() or "access denied" in error_msg.lower():
                        # Permission error - return 403
                        return JSONResponse(
                            status_code=403,
                            content={
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32001,
                                    "message": "Forbidden: Insufficient permissions",
                                    "data": error_msg
                                }
                            }
                        )
                    else:
                        # Other validation error - return 400
                        duration_ms = (time.time() - start_time) * 1000
                        ctx.record_tool_call(
                            tool_name=tool_name,
                            duration_ms=duration_ms,
                            success=False,
                            error=error_msg
                        )
                        return JSONResponse(
                            status_code=200,
                            content={
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32602,
                                    "message": f"Invalid params: {error_msg}"
                                }
                            }
                        )
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    ctx.record_tool_call(
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        success=False,
                        error=str(e)
                    )
                    
                    # Record failed tool invocation
                    metrics_collector.record_tool_invocation(
                        tool_name=tool_name,
                        duration_ms=duration_ms,
                        success=False,
                        request_id=request_id
                    )
                    
                    # Record endpoint request with error
                    request_duration_ms = (time.time() - request_start_time) * 1000
                    metrics_collector.record_endpoint_request(
                        endpoint="/api/v1/mcp",
                        method="POST",
                        duration_ms=request_duration_ms,
                        status_code=500,
                        request_id=request_id
                    )
                    
                    return JSONResponse(
                        status_code=200,
                        content={
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "error": {
                                "code": -32000,
                                "message": f"Internal error: {str(e)}"
                            }
                        }
                    )
        
        else:
            # Unknown method - record endpoint request
            request_duration_ms = (time.time() - request_start_time) * 1000
            metrics_collector.record_endpoint_request(
                endpoint="/api/v1/mcp",
                method="POST",
                duration_ms=request_duration_ms,
                status_code=200,  # JSON-RPC uses 200 even for errors
                request_id=request_id
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            )
    
    except HTTPException:
        # Re-raise HTTPException (auth errors, etc.) - don't catch these
        raise
    except ValidationError as e:
        # Check if it's a permission error
        error_msg = str(e)
        if "permission" in error_msg.lower() or "access denied" in error_msg.lower():
            status_code = 403
        else:
            status_code = 400
        request_duration_ms = (time.time() - request_start_time) * 1000
        metrics_collector.record_endpoint_request(
            endpoint="/api/v1/mcp",
            method="POST",
            duration_ms=request_duration_ms,
            status_code=status_code,
            request_id=request_id
        )
        raise HTTPException(status_code=status_code, detail=error_msg)
    except json.JSONDecodeError:
        request_duration_ms = (time.time() - request_start_time) * 1000
        metrics_collector.record_endpoint_request(
            endpoint="/api/v1/mcp",
            method="POST",
            duration_ms=request_duration_ms,
            status_code=400,
            request_id=request_id
        )
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        request_duration_ms = (time.time() - request_start_time) * 1000
        metrics_collector.record_endpoint_request(
            endpoint="/api/v1/mcp",
            method="POST",
            duration_ms=request_duration_ms,
            status_code=500,
            request_id=request_id
        )
        logger.error(f"Error in MCP endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp")
async def mcp_endpoint(request: Request, authorization: Optional[str] = Header(None)):
    """
    Main MCP protocol endpoint - handles MCP messages over HTTP
    
    Supports MCP protocol messages:
    - initialize
    - tools/list
    - tools/call
    
    Request format (MCP protocol JSON-RPC 2.0):
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list" | "tools/call",
        "params": {...}
    }
    """
    return await handle_mcp_request(request, authorization)


@router.get("/mcp/info")
async def mcp_info():
    """
    MCP server information endpoint
    Returns server capabilities and metadata for Claude Desktop configuration
    """
    return JSONResponse(content={
        "name": "financial-mcp-server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",
        "capabilities": {
            "tools": {
                "listChanged": False
            }
        },
        "server_info": {
            "name": "Financial MCP Server",
            "version": "1.0.0"
        },
        "endpoints": {
            "mcp": "/api/v1/mcp",
            "info": "/api/v1/mcp/info"
        },
        "usage": {
            "initialize": "POST /api/v1/mcp with method: 'initialize'",
            "list_tools": "POST /api/v1/mcp with method: 'tools/list'",
            "call_tool": "POST /api/v1/mcp with method: 'tools/call'"
        }
    })
