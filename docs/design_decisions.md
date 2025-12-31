# Design Decisions

This document outlines key architectural and design decisions made during the development of the Financial MCP Server.

## Architecture Decisions

### 1. Dual Orchestration Strategy

**Decision:** Support both Claude API orchestrator and mock query parsing orchestrator.

**Rationale:**
- Allows development and testing without Claude API access
- Provides fallback when API key is unavailable
- Enables cost-effective development and demos
- Maintains same interface for both approaches

**Implementation:**
- Automatic selection based on `CLAUDE_API_KEY` presence
- Mock orchestrator uses regex-based query parsing
- Both orchestrators implement same interface
- Seamless fallback mechanism

**Trade-offs:**
- Mock orchestrator has limited query understanding
- Claude API provides better natural language understanding
- Mock orchestrator is faster but less intelligent

### 2. Server-Sent Events (SSE) for Streaming

**Decision:** Use SSE instead of WebSockets for reasoning endpoint streaming.

**Rationale:**
- Simpler implementation than WebSockets
- Unidirectional streaming fits reasoning use case
- Better HTTP/2 support
- Easier to debug and monitor
- Standard HTTP infrastructure works out of the box

**Implementation:**
- FastAPI StreamingResponse with SSE format
- Event types: start, thinking, tool_call, tool_result, answer, done, error
- Real-time updates as reasoning progresses
- Client can disconnect and reconnect easily

**Trade-offs:**
- SSE is unidirectional (server → client only)
- WebSockets would allow bidirectional communication
- SSE sufficient for reasoning use case

### 3. MCP Protocol over HTTP

**Decision:** Implement MCP protocol over HTTP using JSON-RPC 2.0.

**Rationale:**
- Claude Desktop supports HTTP transport
- Easier to integrate with existing infrastructure
- Standard HTTP authentication and monitoring
- Better for production deployments
- Supports both stdio and HTTP transports

**Implementation:**
- JSON-RPC 2.0 message format
- Standard MCP methods: initialize, tools/list, tools/call
- Error handling with JSON-RPC error codes
- Request/response correlation via message IDs

**Trade-offs:**
- HTTP adds overhead compared to stdio
- But provides better observability and security

### 4. Role-Based Access Control (RBAC)

**Decision:** Implement fine-grained RBAC with decorators.

**Rationale:**
- Security is critical for financial data
- Need granular permission control
- Different user roles have different access needs
- Decorator pattern keeps code clean
- Easy to test and maintain

**Implementation:**
- Three roles: admin, analyst, viewer
- Permission-based access control
- Decorator pattern for tool protection
- User-specific data access enforcement
- JWT token-based authentication

**Trade-offs:**
- More complex than simple authentication
- But provides necessary security for financial data
- Clear separation of concerns

### 5. Structured Logging with Request IDs

**Decision:** Use JSON-structured logging with request ID propagation.

**Rationale:**
- Essential for debugging distributed systems
- Enables correlation of logs across components
- JSON format easy to parse and query
- Works well with log aggregation tools (Loki, ELK)
- Better observability

**Implementation:**
- Request ID generation at entry point
- Context propagation through all layers
- JSON-formatted log entries
- Request ID in all log messages
- Tool calls tracked with request ID

**Trade-offs:**
- Slightly more overhead than simple logging
- But provides essential observability

### 6. Prometheus Metrics

**Decision:** Use Prometheus for metrics collection.

**Rationale:**
- Industry standard for metrics
- Works well with Grafana
- Easy to integrate
- Good performance
- Rich ecosystem

**Implementation:**
- Prometheus client library
- Custom metrics for tool calls, LLM usage, errors
- Endpoint request metrics
- Database query performance
- Exposed at `/api/v1/metrics`

**Trade-offs:**
- Prometheus pull model vs push model
- But standard and well-supported

### 7. SQLAlchemy ORM

**Decision:** Use SQLAlchemy ORM for database access.

**Rationale:**
- Python standard for database access
- Good abstraction layer
- Connection pooling built-in
- Migration support via Alembic
- Type safety with models

**Implementation:**
- SQLAlchemy 2.0 style
- Declarative models
- Query functions abstract database details
- Connection pooling configured
- Migration support ready

**Trade-offs:**
- ORM overhead vs raw SQL
- But provides better maintainability and safety

### 8. FastAPI Framework

**Decision:** Use FastAPI for the API framework.

**Rationale:**
- Modern Python async framework
- Automatic OpenAPI documentation
- Type hints and validation
- Good performance
- Easy to use

**Implementation:**
- FastAPI application with routers
- Automatic request/response validation
- OpenAPI/Swagger documentation
- Async endpoint support
- Dependency injection

**Trade-offs:**
- Newer framework vs Django/Flask
- But provides better developer experience

## Data Model Decisions

### 1. Transaction Model

**Decision:** Store transactions with risk scores and metadata.

**Rationale:**
- Risk analysis requires transaction history
- Metadata enables filtering and analysis
- Timestamps for time-based queries
- Risk scores pre-calculated for performance

### 2. Portfolio Model

**Decision:** Store portfolios as JSON with asset details.

**Rationale:**
- Flexible asset structure
- Easy to update
- Supports various asset types
- JSON allows schema evolution

### 3. Market Data Model

**Decision:** Store time-series market data.

**Rationale:**
- Historical data for analysis
- Aggregation support
- Time-based queries
- Price and volume tracking

## Security Decisions

### 1. JWT Token Authentication

**Decision:** Use JWT tokens for authentication.

**Rationale:**
- Stateless authentication
- Scalable
- Standard approach
- Easy to implement
- Token expiration support

### 2. Permission-Based Access

**Decision:** Implement permission-based access control.

**Rationale:**
- More flexible than role-only
- Granular control
- Easy to extend
- Clear permission model

## Testing Decisions

### 1. Mock Database for Unit Tests

**Decision:** Mock database responses in unit tests.

**Rationale:**
- Faster test execution
- No database setup required
- Isolated tests
- Easy to test edge cases

### 2. Integration Tests for Endpoints

**Decision:** Use FastAPI TestClient for integration tests.

**Rationale:**
- Tests actual HTTP layer
- Validates end-to-end flow
- Catches integration issues
- Realistic test scenarios

## Observability Decisions

### 1. Request Context Pattern

**Decision:** Use RequestContext for tracing.

**Rationale:**
- Centralized request tracking
- Easy to add new metrics
- Context propagation
- Clean API

### 2. Metrics at Multiple Levels

**Decision:** Collect metrics at endpoint, tool, and database levels.

**Rationale:**
- Comprehensive observability
- Identify bottlenecks
- Track usage patterns
- Performance monitoring

## Deployment Decisions

### 1. Docker Compose for Local Development

**Decision:** Provide Docker Compose setup.

**Rationale:**
- One-command deployment
- Consistent environment
- Easy to share
- Production-like setup

### 2. Environment-Based Configuration

**Decision:** Use environment variables for configuration.

**Rationale:**
- 12-factor app principles
- Easy to configure
- No code changes for different environments
- Secure secret management

## Future Considerations

### Potential Improvements

1. **Caching:** Add Redis for query result caching
2. **Rate Limiting:** Implement rate limiting middleware
3. **WebSocket Support:** Add WebSocket for bidirectional communication
4. **GraphQL API:** Consider GraphQL for flexible queries
5. **Multi-tenancy:** Support multiple organizations
6. **Event Sourcing:** Consider event sourcing for audit trail

### Scalability Considerations

1. **Horizontal Scaling:** Stateless design supports horizontal scaling
2. **Database Sharding:** May need sharding for large datasets
3. **Message Queue:** Consider message queue for async processing
4. **CDN:** Use CDN for static assets
5. **Load Balancing:** Add load balancer for high availability

