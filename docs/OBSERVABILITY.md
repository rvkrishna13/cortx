# Observability Guide

This document describes the observability implementation for the Financial MCP Server, including structured logging, metrics collection, and request tracing.

## Overview

The observability system provides:
- **Structured Logging**: JSON-formatted logs for Grafana/Loki
- **Metrics Collection**: Prometheus-compatible metrics
- **Request Tracing**: Request ID tracking across all operations
- **Tool Call Tracking**: Success/failure counts, latency, and details per request
- **LLM Token Usage**: Input/output token tracking per request
- **Error Tracking**: Error rates by type and endpoint

## Architecture

```
Request → RequestContext (generates request_id)
    ↓
Orchestrator (tracks tool calls, LLM usage)
    ↓
MetricsCollector (aggregates metrics)
    ↓
Structured Logs (JSON) → Grafana/Loki
Metrics (Prometheus) → Prometheus → Grafana
```

## Request ID Tracking

Every request gets a unique `request_id` that is:
- Generated at the start of each request
- Propagated through all operations
- Included in all logs and metrics
- Returned to the client in SSE events

## Metrics Tracked

### 1. Tool Invocation Metrics
- **Count**: Total number of tool calls
- **Latency**: Average latency per tool
- **Errors**: Number of failed tool calls
- **Success Rate**: Percentage of successful calls

Metrics format:
```
tool_query_transactions_count 150
tool_query_transactions_latency_ms 125.5
tool_query_transactions_errors 2
```

### 2. LLM Token Usage
- **Input Tokens**: Tokens sent to Claude
- **Output Tokens**: Tokens received from Claude
- **Total Tokens**: Sum of input + output
- **Calls**: Number of LLM API calls

Metrics format:
```
llm_usage_tokens_input 5000
llm_usage_tokens_output 2000
llm_usage_count 10
```

### 3. Database Query Performance
- **Count**: Number of queries per type
- **Latency**: Average query latency
- **Errors**: Failed queries

Metrics format:
```
db_query_get_transactions_count 200
db_query_get_transactions_latency_ms 45.2
db_query_get_transactions_errors 0
```

### 4. Endpoint Metrics
- **Request Rate**: Requests per second
- **Response Time**: Average response time
- **Status Codes**: Success/error rates

Metrics format:
```
endpoint_POST_/api/v1/reasoning_count 1000
endpoint_POST_/api/v1/reasoning_latency_ms 2500.5
endpoint_POST_/api/v1/reasoning_errors 5
```

### 5. Error Rates
- **Error Count**: Errors by type
- **Error Rate**: Errors per endpoint/tool

Metrics format:
```
error_orchestrator_error_count 2
error_tool_execution_error_count 10
```

## Structured Logging

All logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "logger": "src.services.orchestrator",
  "message": "Tool invocation",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "query_transactions",
  "duration_ms": 150.5,
  "success": true,
  "metric_type": "tool_invocation"
}
```

### Log Fields

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (INFO, ERROR, WARNING, DEBUG)
- `logger`: Logger name
- `message`: Log message
- `request_id`: Request identifier (always present)
- `metric_type`: Type of metric (tool_invocation, llm_usage, etc.)
- Additional fields based on metric type

## Request Context

Each request has a `RequestContext` that tracks:

```python
{
    "request_id": "uuid",
    "tool_calls": {
        "total": 5,
        "succeeded": 4,
        "failed": 1,
        "details": [
            {
                "tool_name": "query_transactions",
                "duration_ms": 150.5,
                "success": true,
                "error": null,
                "timestamp": 1234567890.123
            }
        ]
    },
    "llm_usage": {
        "tokens_input": 5000,
        "tokens_output": 2000,
        "calls": 2
    }
}
```

## Integration Points

### 1. Reasoning Endpoint
- Generates request ID
- Creates RequestContext
- Passes context to orchestrator
- Tracks endpoint metrics

### 2. Orchestrator
- Records tool calls (success/failure, latency)
- Tracks LLM token usage
- Records errors

### 3. MCP Tools
- Tool execution is timed
- Success/failure is tracked
- Errors are logged with context

## Prometheus Integration

### Metrics Endpoint
Access metrics at: `GET /api/v1/metrics`

### Prometheus Configuration
See `prometheus/prometheus.yml` for scraping configuration.

### Scraping
Prometheus scrapes metrics every 10 seconds from:
```
http://localhost:8000/api/v1/metrics
```

## Grafana Dashboard

### Import Dashboard
1. Open Grafana
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/financial-mcp-dashboard.json`

### Dashboard Panels

1. **Request Rate**: Requests per second to reasoning endpoint
2. **Tool Invocation Count**: Count of each tool called
3. **Tool Success vs Failure Rate**: Pie chart of success/failure
4. **Tool Latency**: Average latency per tool
5. **LLM Token Usage**: Input/output tokens over time
6. **Error Rate by Type**: Errors grouped by type
7. **Database Query Performance**: Query latency by type
8. **Endpoint Response Time**: Response time for reasoning endpoint
9. **Tool Calls per Request**: Average tool calls
10. **Total Errors**: Total error count
11. **Total LLM Calls**: Total LLM API calls
12. **Success Rate**: Overall success rate percentage

## Querying Logs in Grafana

### Loki Queries

**Find all tool calls for a request:**
```logql
{job="financial-mcp-server"} |= "tool_invocation" | json | request_id="550e8400-e29b-41d4-a716-446655440000"
```

**Find failed tool calls:**
```logql
{job="financial-mcp-server"} |= "tool_invocation" | json | success="false"
```

**Find requests with high token usage:**
```logql
{job="financial-mcp-server"} |= "llm_usage" | json | total_tokens > 10000
```

**Find errors by type:**
```logql
{job="financial-mcp-server"} |= "error" | json | error_type="tool_execution_error"
```

## Example Queries

### Prometheus Queries

**Tool success rate:**
```promql
(sum(tool_*_count) - sum(tool_*_errors)) / sum(tool_*_count) * 100
```

**Average tool latency:**
```promql
avg(tool_*_latency_ms)
```

**Total tokens used:**
```promql
llm_usage_tokens_input + llm_usage_tokens_output
```

**Error rate:**
```promql
sum(error_*_count) / sum(endpoint_*_count) * 100
```

## Setup Instructions

### 1. Enable Logging
Logging is automatically enabled when the app starts.

### 2. Setup Prometheus
1. Install Prometheus
2. Copy `prometheus/prometheus.yml` to your Prometheus config
3. Start Prometheus

### 3. Setup Grafana
1. Install Grafana
2. Add Prometheus as data source
3. Add Loki as data source (if using)
4. Import dashboard from `grafana/dashboards/financial-mcp-dashboard.json`

### 4. View Metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Metrics endpoint: http://localhost:8000/api/v1/metrics

## Log Examples

### Tool Invocation Log
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "message": "Tool invocation",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "query_transactions",
  "duration_ms": 150.5,
  "success": true,
  "metric_type": "tool_invocation"
}
```

### LLM Usage Log
```json
{
  "timestamp": "2024-01-01T12:00:05.000Z",
  "level": "INFO",
  "message": "LLM usage",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "tokens_input": 5000,
  "tokens_output": 2000,
  "total_tokens": 7000,
  "duration_ms": 2500.5,
  "metric_type": "llm_usage"
}
```

### Error Log
```json
{
  "timestamp": "2024-01-01T12:00:10.000Z",
  "level": "ERROR",
  "message": "Error occurred",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error_type": "tool_execution_error",
  "error_message": "Database connection failed",
  "metric_type": "error"
}
```

## Best Practices

1. **Always include request_id** in logs for traceability
2. **Use structured logging** - add context as JSON fields
3. **Track metrics at key points** - tool calls, LLM usage, errors
4. **Monitor error rates** - set up alerts for high error rates
5. **Track token usage** - monitor LLM costs
6. **Review tool performance** - identify slow tools

