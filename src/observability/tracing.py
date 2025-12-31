"""
Request tracing and context management
"""
from typing import Dict, Any, Optional, Callable
from functools import wraps
import time
from src.observability.logging import generate_request_id, set_request_id, get_request_id, RequestLogger, get_logger
from src.observability.metrics import get_metrics_collector

logger = get_logger(__name__)


class RequestContext:
    """Context manager for request tracing"""
    
    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or generate_request_id()
        self.start_time = time.time()
        self.tool_calls = {
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "details": []
        }
        self.llm_usage = {
            "tokens_input": 0,
            "tokens_output": 0,
            "calls": 0
        }
        self.logger = RequestLogger(self.request_id, logger)
    
    def __enter__(self):
        set_request_id(self.request_id)
        self.logger.info("Request started", request_id=self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        # Log request completion
        self.logger.info(
            "Request completed",
            duration_ms=duration_ms,
            tool_calls_total=self.tool_calls["total"],
            tool_calls_succeeded=self.tool_calls["succeeded"],
            tool_calls_failed=self.tool_calls["failed"],
            llm_tokens_input=self.llm_usage["tokens_input"],
            llm_tokens_output=self.llm_usage["tokens_output"],
            llm_total_tokens=self.llm_usage["tokens_input"] + self.llm_usage["tokens_output"]
        )
        
        # Record endpoint metrics
        metrics = get_metrics_collector()
        # Note: endpoint and status_code should be set by the endpoint handler
        return False
    
    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool, error: Optional[str] = None):
        """Record a tool call"""
        self.tool_calls["total"] += 1
        if success:
            self.tool_calls["succeeded"] += 1
        else:
            self.tool_calls["failed"] += 1
        
        self.tool_calls["details"].append({
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "timestamp": time.time()
        })
        
        # Record in metrics
        metrics = get_metrics_collector()
        metrics.record_tool_invocation(tool_name, duration_ms, success, self.request_id)
    
    def record_llm_call(self, tokens_input: int, tokens_output: int, duration_ms: float):
        """Record LLM usage"""
        self.llm_usage["tokens_input"] += tokens_input
        self.llm_usage["tokens_output"] += tokens_output
        self.llm_usage["calls"] += 1
        
        # Record in metrics
        metrics = get_metrics_collector()
        metrics.record_llm_usage(tokens_input, tokens_output, duration_ms, self.request_id)


def trace_request(func: Optional[Callable] = None, endpoint: Optional[str] = None):
    """Decorator to trace requests"""
    def decorator(f: Callable):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # Get or create request context
            request_id = get_request_id() or generate_request_id()
            
            with RequestContext(request_id) as ctx:
                # Store context in kwargs for access in function
                kwargs["request_context"] = ctx
                
                start_time = time.time()
                try:
                    result = await f(*args, **kwargs)
                    status_code = 200
                    return result
                except Exception as e:
                    status_code = 500
                    ctx.logger.error("Request failed", error=str(e), error_type=type(e).__name__)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    endpoint_name = endpoint or f.__name__
                    
                    # Record endpoint metrics
                    metrics = get_metrics_collector()
                    metrics.record_endpoint_request(
                        endpoint=endpoint_name,
                        method="POST",  # Could be extracted from request
                        duration_ms=duration_ms,
                        status_code=status_code,
                        request_id=request_id
                    )
        
        return wrapper
    return decorator if func is None else decorator(func)


def get_tracer(request_id: Optional[str] = None) -> RequestContext:
    """Get a tracer instance"""
    return RequestContext(request_id)

