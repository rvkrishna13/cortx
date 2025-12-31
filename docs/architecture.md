# Financial MCP Server - Architecture Documentation

## System Architecture Overview

This document provides a comprehensive view of the Financial MCP Server architecture, showing components, data flow, and interactions.

---

## Detailed Component Architecture

### API Endpoints (FastAPI)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/reasoning` | POST | SSE streaming reasoning |
| `/api/v1/mcp` | POST | MCP protocol (JSON-RPC 2.0) |
| `/api/v1/metrics` | GET | Prometheus metrics |

---

### Authentication & Authorization

**Flow:**
```
Request → Extract JWT Token → Validate Token → Extract User → RBAC Check → Allow/Deny
```

**Roles:**
- **Admin**: Full access to all resources
- **Analyst**: Access to assigned users only
- **Viewer**: Read-only public data

**Permissions:**
- `READ_TRANSACTIONS` - Query transaction data
- `READ_RISK_METRICS` - Analyze portfolio risk
- `READ_MARKET_DATA` - Access market data (public)

---

### Service Layer

**Components:**

1. **ReasoningOrchestrator**
   - Uses Claude API for intelligent reasoning
   - Multi-turn tool calling
   - Streaming SSE events
   - Optional (requires API key)

2. **MockReasoningOrchestrator**
   - Query parsing-based tool selection
   - No API costs
   - Good for development/testing
   - Regex pattern matching

3. **Streaming Service**
   - Formats events as SSE
   - Progressive updates
   - Real-time user feedback

4. **Risk Analyzer**
   - Calculates volatility
   - Sharpe ratio
   - Value at Risk (VaR)
   - Portfolio metrics

---

### MCP Tools

**Tool 1: query_transactions**

**Purpose:** Fetch transaction data with filters

**Parameters:**
- `user_id` (integer)
- `category` (string)
- `start_date` (ISO date)
- `end_date` (ISO date)
- `min_amount` (number)
- `max_amount` (number)
- `min_risk_score` (0.0-1.0)
- `max_risk_score` (0.0-1.0)
- `limit` (integer, default: 100)

**RBAC:** Requires `READ_TRANSACTIONS` permission

---

**Tool 2: analyze_risk_metrics**

**Purpose:** Calculate portfolio risk indicators

**Parameters:**
- `portfolio_id` (integer)
- `user_id` (integer)
- `period_days` (integer, default: 30)

**Returns:**
- Volatility
- Sharpe Ratio
- Value at Risk
- Average Return
- Risk Level (LOW/MODERATE/HIGH)

**RBAC:** Requires `READ_RISK_METRICS` permission

---

**Tool 3: get_market_summary**

**Purpose:** Get aggregated market data

**Parameters:**
- `symbols` (array of strings)
- `period` ("hour", "day", "week", "month")

**Returns:**
- Current prices
- Price ranges
- Volume statistics
- Price changes

**RBAC:** Requires `READ_MARKET_DATA` permission (available to all roles)

---

### Data Layer

**Database:** PostgreSQL 14+

**Tables:**

1. **transactions**
   - id (primary key)
   - user_id
   - amount
   - currency
   - timestamp
   - category
   - risk_score

2. **portfolios**
   - id (primary key)
   - user_id
   - assets (JSON)
   - total_value
   - last_updated

3. **market_data**
   - id (primary key)
   - symbol
   - price
   - volume
   - timestamp

**ORM:** SQLAlchemy with async support

**Features:**
- Connection pooling (pool_size=10)
- Automatic reconnection
- Query optimization
- Migration support (Alembic)

---

### Observability

**Logging:**
- Structured JSON format
- Request ID propagation
- Log levels: DEBUG, INFO, WARNING, ERROR
- File output: `./logs/app.log`

**Metrics:**
- Request count
- Request latency
- Error rate
- Tool usage statistics
- Database query performance

**Tracing:**
- Request ID tracking
- Tool call duration
- Database query timing

**Stack:**
- Promtail → Loki (log aggregation)
- Prometheus (metrics storage)
- Grafana (visualization)

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Auth | JWT (python-jose) |
| Validation | Pydantic |
| Logging | Structured JSON logging |
| Metrics | Prometheus |
| Visualization | Grafana |
| Containerization | Docker Compose |

---

## Security

- JWT token-based authentication
- Role-based access control (RBAC)
- Permission-based tool access
- Request validation (Pydantic)
- SQL injection protection (ORM)

---

## Configuration

### Required Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/financial_mcp
JWT_SECRET_KEY=your-secret-key-here
```

### Optional

```bash
CLAUDE_API_KEY=your-claude-api-key  # Optional, uses mock if not set
LOG_FILE=logs/app.log
DEBUG=True
```

---

See [Setup Guide](setup_guide.md) for detailed setup instructions.