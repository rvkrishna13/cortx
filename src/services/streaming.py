"""
Streaming utilities for Server-Sent Events (SSE)
"""
import json
from typing import Dict, Any, AsyncGenerator


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format data as Server-Sent Event
    
    Args:
        event_type: Type of event (thinking, tool_call, tool_result, answer, error, done)
        data: Event data dictionary
    
    Returns:
        Formatted SSE string
    """
    payload = {
        "type": event_type,
        "data": data
    }
    return f"data: {json.dumps(payload)}\n\n"


async def stream_reasoning_results(
    orchestrator_results: AsyncGenerator[Dict[str, Any], None]
) -> AsyncGenerator[str, None]:
    """
    Convert orchestrator results to SSE format
    
    Args:
        orchestrator_results: Async generator from ReasoningOrchestrator.reason()
    
    Yields:
        SSE-formatted strings
    """
    try:
        # Send start event
        yield format_sse_event("start", {"message": "Starting reasoning"})
        
        async for event in orchestrator_results:
            event_type = event.get("type")
            content = event.get("content", "")
            step_number = event.get("step_number", 0)
            
            if event_type == "thinking":
                yield format_sse_event("thinking", {
                    "step_number": step_number,
                    "content": content
                })
            
            elif event_type == "tool_call":
                yield format_sse_event("tool_call", {
                    "step_number": step_number,
                    "tool_name": event.get("tool_name"),
                    "tool_arguments": event.get("tool_arguments", {}),
                    "message": content
                })
            
            elif event_type == "tool_result":
                yield format_sse_event("tool_result", {
                    "step_number": step_number,
                    "tool_name": event.get("tool_name"),
                    "result": event.get("tool_result", ""),
                    "message": content
                })
            
            elif event_type == "answer":
                yield format_sse_event("answer", {
                    "step_number": step_number,
                    "content": content
                })
            
            elif event_type == "error":
                yield format_sse_event("error", {
                    "step_number": step_number,
                    "message": content
                })
                break
            
            elif event_type == "done":
                yield format_sse_event("done", {
                    "step_number": step_number,
                    "final_answer": event.get("final_answer", ""),
                    "tool_calls_made": event.get("tool_calls_made", 0),
                    "message": "Reasoning complete"
                })
                break
        
    except Exception as e:
        yield format_sse_event("error", {
            "message": f"Streaming error: {str(e)}"
        })

