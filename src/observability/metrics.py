"""
Metrics collection for Prometheus/Grafana
"""
import time
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from threading import Lock
from src.observability.logging import get_logger, get_request_id

logger = get_logger(__name__)


class MetricsCollector:
    """Collects metrics for observability"""
    
    def __init__(self):
        self._lock = Lock()
        self._metrics = defaultdict(lambda: {
            "count": 0,
            "total_latency_ms": 0.0,
            "errors": 0,
            "last_updated": None
        })
    
    def record_tool_invocation(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        request_id: Optional[str] = None
    ):
        """Record MCP tool invocation"""
        with self._lock:
            metric = self._metrics[f"tool_{tool_name}"]
            metric["count"] += 1
            metric["total_latency_ms"] += duration_ms
            if not success:
                metric["errors"] += 1
            metric["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "Tool invocation",
            extra={
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "success": success,
                "request_id": request_id or get_request_id(),
                "metric_type": "tool_invocation"
            }
        )
    
    def record_llm_usage(
        self,
        tokens_input: int,
        tokens_output: int,
        duration_ms: float,
        request_id: Optional[str] = None
    ):
        """Record LLM token usage"""
        with self._lock:
            metric = self._metrics["llm_usage"]
            metric["count"] += 1
            metric["total_latency_ms"] += duration_ms
            metric["tokens_input"] = metric.get("tokens_input", 0) + tokens_input
            metric["tokens_output"] = metric.get("tokens_output", 0) + tokens_output
            metric["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "LLM usage",
            extra={
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "total_tokens": tokens_input + tokens_output,
                "duration_ms": duration_ms,
                "request_id": request_id or get_request_id(),
                "metric_type": "llm_usage"
            }
        )
    
    def record_database_query(
        self,
        query_type: str,
        duration_ms: float,
        success: bool,
        request_id: Optional[str] = None
    ):
        """Record database query performance"""
        with self._lock:
            metric = self._metrics[f"db_query_{query_type}"]
            metric["count"] += 1
            metric["total_latency_ms"] += duration_ms
            if not success:
                metric["errors"] += 1
            metric["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "Database query",
            extra={
                "query_type": query_type,
                "duration_ms": duration_ms,
                "success": success,
                "request_id": request_id or get_request_id(),
                "metric_type": "database_query"
            }
        )
    
    def record_endpoint_request(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        request_id: Optional[str] = None
    ):
        """Record API endpoint request"""
        success = 200 <= status_code < 300
        with self._lock:
            metric = self._metrics[f"endpoint_{method}_{endpoint}"]
            metric["count"] += 1
            metric["total_latency_ms"] += duration_ms
            if not success:
                metric["errors"] += 1
            metric["last_updated"] = datetime.utcnow().isoformat()
        
        logger.info(
            "Endpoint request",
            extra={
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "success": success,
                "request_id": request_id or get_request_id(),
                "metric_type": "endpoint_request"
            }
        )
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        """Record error occurrence"""
        with self._lock:
            metric = self._metrics[f"error_{error_type}"]
            metric["count"] += 1
            metric["errors"] += 1
            metric["last_updated"] = datetime.utcnow().isoformat()
        
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "request_id": request_id or get_request_id(),
            "metric_type": "error"
        }
        if context:
            log_data.update(context)
        
        logger.error("Error occurred", extra=log_data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self._lock:
            return dict(self._metrics)
    
    def _sanitize_metric_name(self, name: str) -> str:
        """Sanitize metric name for Prometheus (replace invalid characters)"""
        # Prometheus metric names must match: [a-zA-Z_:][a-zA-Z0-9_:]*
        # Replace / with _ and remove leading/trailing underscores from replacements
        sanitized = name.replace("/", "_").replace("-", "_")
        # Remove multiple consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized
    
    def get_prometheus_format(self) -> str:
        """Get metrics in Prometheus format"""
        lines = []
        with self._lock:
            for metric_name, data in self._metrics.items():
                # Sanitize metric name for Prometheus
                sanitized_name = self._sanitize_metric_name(metric_name)
                
                # Count metric
                lines.append(f"# TYPE {sanitized_name}_count counter")
                lines.append(f"{sanitized_name}_count {data['count']}")
                
                # Latency metric
                avg_latency = data["total_latency_ms"] / data["count"] if data["count"] > 0 else 0
                lines.append(f"# TYPE {sanitized_name}_latency_ms gauge")
                lines.append(f"{sanitized_name}_latency_ms {avg_latency}")
                
                # Error count
                lines.append(f"# TYPE {sanitized_name}_errors counter")
                lines.append(f"{sanitized_name}_errors {data['errors']}")
        
        return "\n".join(lines)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

