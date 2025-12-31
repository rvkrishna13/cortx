"""
Reasoning endpoint - Streaming reasoning with MCP tools using Server-Sent Events (SSE)
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import time
from src.api.schemas.reasoning import ReasoningRequest
from src.database.connection import database
from sqlalchemy.orm import Session
from src.services.orchestrator import ReasoningOrchestrator
from src.services.mock_orchestrator import MockReasoningOrchestrator
from src.services.streaming import format_sse_event
from src.utils.exceptions import ValidationError
from src.observability.tracing import RequestContext, generate_request_id
from src.observability.logging import set_request_id
from src.observability.metrics import get_metrics_collector
from src.config.settings import settings
from src.auth.jwt_auth import extract_user_from_token
from src.auth.rbac import get_user_from_context

router = APIRouter()
metrics_collector = get_metrics_collector()


@router.post("/reasoning")
async def reasoning_endpoint(
    request: ReasoningRequest,
    db: Session = Depends(database.get_session),
    authorization: Optional[str] = Header(None)
):
    """
    Reasoning endpoint using Server-Sent Events (SSE) for real-time streaming.
    Streams reasoning steps, tool calls, and final answer as they happen.
    
    This endpoint automatically uses:
    - Claude API orchestrator if CLAUDE_API_KEY is set
    - Mock orchestrator (query parsing) if CLAUDE_API_KEY is not set
    
    This endpoint provides real-time updates via SSE, allowing clients to see:
    - Thinking process (or query parsing in mock mode)
    - Tool calls as they're executed
    - Tool results as they're received
    - Final answer streamed in chunks
    
    Example queries:
    - "Analyze high-risk transactions from the last week for user 1"
    - "What is the market summary for AAPL and GOOGL?"
    - "Show me the risk metrics for portfolio 5"
    
    Response format (SSE):
    - Event: "start" - Initial connection established
    - Event: "thinking" - Reasoning/parsing process
    - Event: "tool_call" - Tool execution started
    - Event: "tool_result" - Tool execution completed
    - Event: "answer" - Final answer chunks
    - Event: "done" - Reasoning complete
    - Event: "error" - Error occurred
    """
    # Generate request ID and set up tracing
    request_id = generate_request_id()
    set_request_id(request_id)
    request_start_time = time.time()
    
    try:
        # Authorization is required - reject if not provided
        if not authorization:
            request_duration_ms = (time.time() - request_start_time) * 1000
            metrics_collector.record_endpoint_request(
                endpoint="/api/v1/reasoning",
                method="POST",
                duration_ms=request_duration_ms,
                status_code=401,
                request_id=request_id
            )
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Authorization token is required"
            )
        
        # Extract auth context from header and validate early
        # Handle "Bearer " prefix if present
        token = authorization
        if token and token.startswith("Bearer "):
            token = token[7:]
        auth_context = {"token": token}
        # Validate token early to return proper HTTP status codes
        try:
            user_info = get_user_from_context(auth_context)
        except ValidationError as e:
            # Invalid token - return 401
            request_duration_ms = (time.time() - request_start_time) * 1000
            metrics_collector.record_endpoint_request(
                endpoint="/api/v1/reasoning",
                method="POST",
                duration_ms=request_duration_ms,
                status_code=401,
                request_id=request_id
            )
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Invalid or expired token"
            )
        
        # Create request context for tracing
        ctx = RequestContext(request_id)
        ctx.__enter__()
        
        # Use mock orchestrator if Claude API key is not available
        # Check for None, empty string, or placeholder values
        api_key = settings.CLAUDE_API_KEY
        placeholder_values = ["", "your_claude_api_key_here", "your-secret-key-change-in-production"]
        has_valid_claude_key = (
            api_key and 
            api_key.strip() and 
            api_key.strip() not in placeholder_values
        )
        
        if not has_valid_claude_key:
            orchestrator = MockReasoningOrchestrator(request_context=ctx)
        else:
            try:
                orchestrator = ReasoningOrchestrator(request_context=ctx)
            except ValidationError:
                # Fallback to mock if orchestrator creation fails (e.g., API key validation)
                orchestrator = MockReasoningOrchestrator(request_context=ctx)
        
        # Stream results as SSE - stream immediately as events arrive
        async def generate_stream() -> AsyncGenerator[str, None]:
            import asyncio
            buffer_size = 0
            max_buffer = 100  # Max events in buffer before backpressure
            
            try:
                # Generate reasoning results
                reasoning_results = orchestrator.reason(
                    query=request.query,
                    user_id=request.user_id,
                    auth_context=auth_context,
                    include_thinking=request.include_thinking
                )
                
                # Send initial start event with request ID
                yield format_sse_event("start", {
                    "message": "Starting reasoning",
                    "query": request.query,
                    "request_id": request_id
                })
                
                # Stream events as they come from orchestrator with backpressure handling
                async for event in reasoning_results:
                    # Backpressure: if buffer is full, wait briefly before yielding
                    if buffer_size >= max_buffer:
                        await asyncio.sleep(0.1)  # Wait 100ms to allow client to catch up
                        buffer_size = 0  # Reset buffer counter
                    event_type = event.get("type")
                    content = event.get("content", "")
                    step_number = event.get("step_number", 0)
                    
                    # Stream each event type immediately
                    if event_type == "thinking":
                        yield format_sse_event("thinking", {
                            "step_number": step_number,
                            "content": content
                        })
                        buffer_size += 1
                    
                    elif event_type == "tool_call":
                        # Only send tool name, not full arguments
                        yield format_sse_event("tool_call", {
                            "step_number": step_number,
                            "tool_name": event.get("tool_name"),
                            "message": content
                        })
                        buffer_size += 1
                    
                    elif event_type == "tool_result":
                        # Only send success status, not full result data
                        yield format_sse_event("tool_result", {
                            "step_number": step_number,
                            "tool_name": event.get("tool_name"),
                            "success": not event.get("is_error", False),
                            "message": content
                        })
                        buffer_size += 1
                    
                    elif event_type == "answer":
                        # Ensure content is a dict/object, not a string
                        answer_content = content
                        if isinstance(content, str):
                            try:
                                import json
                                answer_content = json.loads(content)
                            except (json.JSONDecodeError, TypeError):
                                # If parsing fails, wrap in a simple structure
                                answer_content = {"text": content}
                        
                        yield format_sse_event("answer", {
                            "step_number": step_number,
                            "content": answer_content
                        })
                        buffer_size += 1
                    
                    elif event_type == "error":
                        yield format_sse_event("error", {
                            "step_number": step_number,
                            "message": content
                        })
                        break
                    
                    elif event_type == "done":
                        # Ensure final_answer is a dict/object, not a string
                        final_answer = event.get("final_answer", {})
                        if isinstance(final_answer, str):
                            try:
                                import json
                                final_answer = json.loads(final_answer)
                            except (json.JSONDecodeError, TypeError):
                                # If parsing fails, wrap in a simple structure
                                final_answer = {"text": final_answer} if final_answer else {}
                        
                        yield format_sse_event("done", {
                            "step_number": step_number,
                            "final_answer": final_answer,
                            "tool_calls_made": event.get("tool_calls_made", 0),
                            "message": "Reasoning complete"
                        })
                        break
                
            except ValidationError as e:
                # Re-raise ValidationError so it can be caught by the top-level handler
                # This allows the top-level exception handler to convert it to HTTPException
                raise
            except Exception as e:
                yield format_sse_event("error", {"message": str(e)})
            finally:
                # Exit request context when streaming completes
                ctx.__exit__(None, None, None)
                
                # Record endpoint request metrics
                request_duration_ms = (time.time() - request_start_time) * 1000
                metrics_collector.record_endpoint_request(
                    endpoint="/api/v1/reasoning",
                    method="POST",
                    duration_ms=request_duration_ms,
                    status_code=200,
                    request_id=request_id
                )
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for real-time streaming
            }
        )
    
    except ValidationError as e:
        request_duration_ms = (time.time() - request_start_time) * 1000
        # Check if it's an auth error
        if e.field in ("token", "auth"):
            status_code = 401
            detail = "Unauthorized: Invalid or expired token"
        elif "permission" in e.message.lower() or "access denied" in e.message.lower():
            status_code = 403
            detail = "Forbidden: Insufficient permissions"
        else:
            status_code = 400
            detail = str(e)
        
        metrics_collector.record_endpoint_request(
            endpoint="/api/v1/reasoning",
            method="POST",
            duration_ms=request_duration_ms,
            status_code=status_code,
            request_id=request_id
        )
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        # Re-raise HTTPException (auth errors, etc.) - don't catch these
        raise
    except Exception as e:
        request_duration_ms = (time.time() - request_start_time) * 1000
        metrics_collector.record_endpoint_request(
            endpoint="/api/v1/reasoning",
            method="POST",
            duration_ms=request_duration_ms,
            status_code=500,
            request_id=request_id
        )
        raise HTTPException(status_code=500, detail=f"Error setting up streaming: {str(e)}")

