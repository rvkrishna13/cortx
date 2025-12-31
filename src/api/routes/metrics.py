"""
Metrics endpoint for Prometheus scraping
"""
from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from src.observability.metrics import get_metrics_collector

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint
    Exposes metrics in Prometheus format for scraping
    """
    metrics = get_metrics_collector()
    prometheus_format = metrics.get_prometheus_format()
    
    return Response(
        content=prometheus_format,
        media_type="text/plain; version=0.0.4"
    )


@router.get("/metrics/json")
async def metrics_json_endpoint():
    """
    Metrics endpoint in JSON format for easy reading
    Returns all collected metrics with counts, latencies, and errors
    """
    metrics_collector = get_metrics_collector()
    all_metrics = metrics_collector.get_metrics()
    
    # Format metrics for better readability
    formatted_metrics = {}
    for metric_name, data in all_metrics.items():
        avg_latency = data["total_latency_ms"] / data["count"] if data["count"] > 0 else 0
        formatted_metrics[metric_name] = {
            "count": data["count"],
            "total_latency_ms": data["total_latency_ms"],
            "average_latency_ms": round(avg_latency, 2),
            "errors": data["errors"],
            "success_rate": round((data["count"] - data["errors"]) / data["count"] * 100, 2) if data["count"] > 0 else 100.0,
            "last_updated": data["last_updated"]
        }
        
        # Add LLM-specific metrics if available
        if "llm_usage" in metric_name:
            formatted_metrics[metric_name]["tokens_input"] = data.get("tokens_input", 0)
            formatted_metrics[metric_name]["tokens_output"] = data.get("tokens_output", 0)
            formatted_metrics[metric_name]["total_tokens"] = data.get("tokens_input", 0) + data.get("tokens_output", 0)
    
    return JSONResponse(content={
        "metrics": formatted_metrics,
        "summary": {
            "total_metrics": len(formatted_metrics),
            "total_invocations": sum(m["count"] for m in formatted_metrics.values()),
            "total_errors": sum(m["errors"] for m in formatted_metrics.values()),
            "overall_success_rate": round(
                (sum(m["count"] for m in formatted_metrics.values()) - sum(m["errors"] for m in formatted_metrics.values())) 
                / sum(m["count"] for m in formatted_metrics.values()) * 100, 2
            ) if sum(m["count"] for m in formatted_metrics.values()) > 0 else 100.0
        }
    })

