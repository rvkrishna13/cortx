# Financial MCP Server - Architecture Diagram

## System Architecture Overview

This document provides a comprehensive view of the Financial MCP Server architecture, showing components, data flow, and interactions.

## Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        CD[Claude Desktop<br/>MCP Protocol]
        API[API Clients<br/>HTTP/REST]
        WEB[Web Dashboard<br/>SSE Streaming]
    end

    subgraph "API Gateway Layer"
        FASTAPI[FastAPI Application<br/>CORS, Middleware]
        
        subgraph "API Routes"
            REASONING[/api/v1/reasoning<br/>SSE Streaming]
            MCP[/api/v1/mcp<br/>JSON-RPC 2.0]
            METRICS[/api/v1/metrics<br/>Prometheus]
            HEALTH[/health<br/>Health Check]
        end
    end

    subgraph "Authentication & Authorization"
        JWT[JWT Auth<br/>Token Validation]
        RBAC[RBAC Engine<br/>Role/Permission Checks]
        PERMS[Permissions<br/>Admin, Analyst, Viewer]
    end

    subgraph "Service Layer"
        ORCH[ReasoningOrchestrator<br/>Claude API Integration]
        MOCK[MockReasoningOrchestrator<br/>Query Parsing]
        STREAM[Streaming Service<br/>SSE Formatting]
        RISK[Risk Analyzer<br/>Portfolio Metrics]
    end

    subgraph "MCP Tools Layer"
        TOOLS[MCP Tools Dispatcher]
        QT[query_transactions<br/>Transaction Queries]
        ARM[analyze_risk_metrics<br/>Risk Analysis]
        GMS[get_market_summary<br/>Market Data]
    end

    subgraph "Data Layer"
        DB[(PostgreSQL Database)]
        QUERIES[Query Functions<br/>SQLAlchemy ORM]
        MODELS[Data Models<br/>Transaction, Portfolio, MarketData]
    end

    subgraph "Observability Layer"
        LOG[Structured Logging<br/>JSON Format]
        MET[Metrics Collector<br/>Prometheus]
        TRACE[Request Tracing<br/>Request IDs]
    end

    subgraph "External Services"
        CLAUDE[Claude API<br/>Anthropic]
    end

    %% Client to API connections
    CD -->|MCP Protocol| MCP
    API -->|HTTP/REST| REASONING
    API -->|HTTP/REST| MCP
    WEB -->|SSE Stream| REASONING

    %% API routing
    FASTAPI --> REASONING
    FASTAPI --> MCP
    FASTAPI --> METRICS
    FASTAPI --> HEALTH

    %% Authentication flow
    REASONING --> JWT
    MCP --> JWT
    JWT --> RBAC
    RBAC --> PERMS

    %% Service layer connections
    REASONING --> ORCH
    REASONING --> MOCK
    REASONING --> STREAM
    ORCH --> CLAUDE
    MOCK --> TOOLS
    ORCH --> TOOLS

    %% MCP Tools to Data
    TOOLS --> QT
    TOOLS --> ARM
    TOOLS --> GMS
    QT --> RBAC
    ARM --> RBAC
    GMS --> RBAC
    QT --> QUERIES
    ARM --> QUERIES
    ARM --> RISK
    GMS --> QUERIES

    %% Data layer
    QUERIES --> MODELS
    MODELS --> DB

    %% Observability connections
    REASONING --> LOG
    REASONING --> MET
    REASONING --> TRACE
    MCP --> LOG
    MCP --> MET
    TOOLS --> MET
    ORCH --> MET
    ORCH --> TRACE

    %% Styling
    classDef clientLayer fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef apiLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef authLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef serviceLayer fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef toolLayer fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef dataLayer fill:#e0f2f1,stroke:#004d40,stroke-width:2px
    classDef obsLayer fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef extLayer fill:#fafafa,stroke:#424242,stroke-width:2px

    class CD,API,WEB clientLayer
    class FASTAPI,REASONING,MCP,METRICS,HEALTH apiLayer
    class JWT,RBAC,PERMS authLayer
    class ORCH,MOCK,STREAM,RISK serviceLayer
    class TOOLS,QT,ARM,GMS toolLayer
    class DB,QUERIES,MODELS dataLayer
    class LOG,MET,TRACE obsLayer
    class CLAUDE extLayer
```

## Component Details

### 1. Client Layer
- **Claude Desktop**: Connects via MCP protocol (stdio/HTTP)
- **API Clients**: REST API consumers
- **Web Dashboard**: Real-time SSE streaming interface

### 2. API Gateway Layer (FastAPI)
- **FastAPI Application**: Main application with CORS and middleware
- **Routes**:
  - `/api/v1/reasoning`: SSE streaming endpoint for natural language queries
  - `/api/v1/mcp`: MCP protocol over HTTP (JSON-RPC 2.0)
  - `/api/v1/metrics`: Prometheus metrics endpoint
  - `/health`: Health check endpoint

### 3. Authentication & Authorization
- **JWT Auth**: Token creation, validation, and user extraction
- **RBAC Engine**: Role-based access control with decorators
- **Permissions**: Three roles (Admin, Analyst, Viewer) with granular permissions

### 4. Service Layer
- **ReasoningOrchestrator**: Uses Claude API for intelligent tool selection
- **MockReasoningOrchestrator**: Query parsing-based tool selection (fallback)
- **Streaming Service**: Formats events as Server-Sent Events (SSE)
- **Risk Analyzer**: Calculates portfolio risk metrics (volatility, Sharpe ratio, VaR)

### 5. MCP Tools Layer
- **MCP Tools Dispatcher**: Routes tool calls to appropriate handlers
- **query_transactions**: Query transaction data with filters
- **analyze_risk_metrics**: Analyze portfolio risk metrics
- **get_market_summary**: Get aggregated market data

### 6. Data Layer
- **PostgreSQL Database**: Primary data store
- **Query Functions**: SQLAlchemy ORM-based query functions
- **Data Models**: Transaction, Portfolio, MarketData models

### 7. Observability Layer
- **Structured Logging**: JSON-formatted logs with request IDs
- **Metrics Collector**: Prometheus-compatible metrics
- **Request Tracing**: Request ID propagation and tool call tracking

### 8. External Services
- **Claude API**: Anthropic's Claude API for reasoning (optional)

## Data Flow

### Reasoning Flow (SSE Streaming)
```
Client → /api/v1/reasoning → JWT Auth → RBAC Check → 
Orchestrator → Tool Selection → MCP Tools → Database Queries → 
Results → Streaming Service → SSE Events → Client
```

### MCP Protocol Flow
```
Claude Desktop → /api/v1/mcp → JWT Auth → RBAC Check → 
MCP Tools → Database Queries → Results → JSON-RPC Response → Claude Desktop
```

### Authentication Flow
```
Request → Extract Token → JWT Validation → Extract User → 
RBAC Check → Permission Validation → Allow/Deny
```

## Key Features

1. **Dual Orchestration**: Supports both Claude API and mock query parsing
2. **Streaming**: Real-time SSE streaming for reasoning steps
3. **RBAC**: Fine-grained role-based access control
4. **Observability**: Comprehensive logging, metrics, and tracing
5. **MCP Protocol**: Full MCP protocol support for Claude Desktop
6. **Database Abstraction**: SQLAlchemy ORM with connection pooling

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (python-jose)
- **Streaming**: Server-Sent Events (SSE)
- **Protocol**: MCP (Model Context Protocol)
- **Observability**: Prometheus metrics, structured JSON logging
- **External API**: Claude API (Anthropic)

## Security

- JWT token-based authentication
- Role-based access control (RBAC)
- Permission-based tool access
- User-specific data access rules
- CORS middleware for API protection

## Scalability

- Database connection pooling
- Async/await for concurrent requests
- Streaming responses for large data
- Metrics collection for performance monitoring
- Request tracing for debugging

