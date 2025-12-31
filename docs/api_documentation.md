# API Documentation

Complete API reference for the Financial MCP Server, including all endpoints and MCP tools.

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints require JWT token authentication via the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

## Endpoints

### 1. Health Check

**GET** `/health`

Check server health status.

**Response:**
```json
{
  "status": "healthy"
}
```

### 2. Reasoning Endpoint

**POST** `/api/v1/reasoning`

Streaming reasoning endpoint using Server-Sent Events (SSE) for natural language queries.

**Request Body:**
```json
{
  "query": "Analyze high-risk transactions from the last week for user 1",
  "include_thinking": true,
  "user_id": null
}
```

**Response:** Server-Sent Events stream

**Event Types:**
- `start`: Initial connection established
- `thinking`: Reasoning/parsing process
- `tool_call`: Tool execution started
- `tool_result`: Tool execution completed
- `answer`: Final answer
- `done`: Reasoning complete
- `error`: Error occurred

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/reasoning \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "Get market summary for AAPL",
    "include_thinking": true
  }'
```

### 3. MCP Protocol Endpoint

**POST** `/api/v1/mcp`

MCP protocol endpoint using JSON-RPC 2.0.

#### Initialize

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    }
  }
}
```

#### List Tools

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "query_transactions",
        "description": "...",
        "inputSchema": {...}
      }
    ]
  }
}
```

#### Call Tool

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "query_transactions",
    "arguments": {
      "user_id": 1,
      "limit": 10
    }
  }
}
```

### 4. Metrics Endpoint

**GET** `/api/v1/metrics`

Prometheus-compatible metrics endpoint.

**Response:** Prometheus metrics format

## MCP Tools

### 1. query_transactions

Query transaction data with various filters.

**Parameters:**
- `user_id` (integer, optional): Filter by user ID
- `category` (string, optional): Filter by transaction category
- `currency` (string, optional): Filter by currency (USD, EUR, etc.)
- `start_date` (string, optional): Start date in ISO format (YYYY-MM-DD)
- `end_date` (string, optional): End date in ISO format (YYYY-MM-DD)
- `min_amount` (number, optional): Minimum transaction amount
- `max_amount` (number, optional): Maximum transaction amount
- `min_risk_score` (number, optional): Minimum risk score (0.0-1.0)
- `max_risk_score` (number, optional): Maximum risk score (0.0-1.0)
- `limit` (integer, optional): Maximum number of results (default: 100)

**Example:**
```json
{
  "name": "query_transactions",
  "arguments": {
    "user_id": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "min_risk_score": 0.7,
    "limit": 50
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Transaction ID: 1\nUser ID: 1\nAmount: $1000.00\n..."
    }
  ],
  "isError": false
}
```

**Permissions:** `READ_TRANSACTIONS` or `READ_USER_TRANSACTIONS`

### 2. analyze_risk_metrics

Calculate comprehensive risk indicators for a portfolio.

**Parameters:**
- `portfolio_id` (integer, optional): Portfolio ID to analyze
- `user_id` (integer, optional): User ID to analyze all portfolios
- `period_days` (integer, optional): Number of days to analyze (default: 30)

**Example:**
```json
{
  "name": "analyze_risk_metrics",
  "arguments": {
    "portfolio_id": 2,
    "period_days": 60
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Portfolio 2 Risk Analysis:\n\nPortfolio Value: $17,500.00\nVolatility: 15.00%\nSharpe Ratio: 1.50\n..."
    }
  ],
  "isError": false
}
```

**Metrics Calculated:**
- Volatility (annualized)
- Sharpe Ratio
- Value at Risk (95%)
- Average Return (annualized)
- Maximum Drawdown
- Risk Level (LOW/MODERATE/HIGH)

**Permissions:** `READ_RISK_METRICS`

### 3. get_market_summary

Retrieve aggregated market data including prices, volumes, and trends.

**Parameters:**
- `symbols` (array of strings, optional): List of symbols to include (default: all)
- `period` (string, optional): Aggregation period - "hour", "day", "week", "month" (default: "day")

**Example:**
```json
{
  "name": "get_market_summary",
  "arguments": {
    "symbols": ["AAPL", "GOOGL"],
    "period": "week"
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Market Summary:\n\nAAPL:\n  Current Price: $175.50\n  Average Price: $175.00\n..."
    }
  ],
  "isError": false
}
```

**Permissions:** `READ_MARKET_DATA` (all roles)

## Error Responses

### Authentication Error

**Status:** 401 Unauthorized

```json
{
  "detail": "Unauthorized: Invalid or expired token"
}
```

### Permission Error

**Status:** 403 Forbidden

```json
{
  "detail": "Forbidden: Missing required permissions"
}
```

### Validation Error

**Status:** 400 Bad Request

```json
{
  "detail": "Validation error: Invalid parameter"
}
```

### Tool Error

**Status:** 200 (JSON-RPC uses 200 for errors)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error: Tool execution failed"
  }
}
```

## Example Queries

### Multi-Step Reasoning

**Query:** "Analyze high-risk transactions from the last week for user 1"

**Flow:**
1. Parse query → Identify `query_transactions` tool
2. Extract parameters: `user_id=1`, `start_date=last_week`, `min_risk_score=0.7`
3. Call `query_transactions` tool
4. Analyze results
5. Stream final answer

**SSE Events:**
```
data: {"type":"start","data":{"message":"Starting reasoning"}}
data: {"type":"thinking","data":{"content":"Analyzing query..."}}
data: {"type":"tool_call","data":{"tool_name":"query_transactions"}}
data: {"type":"tool_result","data":{"tool_name":"query_transactions","success":true}}
data: {"type":"answer","data":{"content":"Found 5 high-risk transactions..."}}
data: {"type":"done","data":{"final_answer":"..."}}
```

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:

```
http://localhost:8000/docs
```

This provides:
- Interactive API explorer
- Request/response schemas
- Try-it-out functionality
- Authentication testing

