# Financial MCP Server

A production-ready Financial MCP (Model Context Protocol) server with AI-powered reasoning capabilities, built with FastAPI, PostgreSQL, and Claude API integration.

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- Ports available: 8000, 5432, 9090, 3000

### Using Docker Compose (Recommended for Local Development)

**Step 1: Clone and navigate to the project**
```bash
git clone <repository-url>
cd cortx
```

**Step 2: Start all services**
```bash
make docker-up
```

This single command will:
- Start PostgreSQL database container
- Wait for database to be ready
- Run database seed script (first time only)
- Start FastAPI server
- Start Prometheus for metrics
- Start Grafana for dashboards
- Generate and display admin JWT token

**Step 3: View logs (optional)**
```bash
# View app logs
make docker-logs

# View all service logs
make docker-logs-all
```

**Step 4: Access the services**

Once containers are running, access:

- **API Server**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)

**Step 5: Get your admin token**

The admin JWT token is automatically displayed in the logs when services start. You can also generate it manually:

```bash
make docker-token
```

**Step 6: Test the API**

```bash
# Get your token from logs, then:
curl -X POST http://localhost:8000/api/v1/reasoning \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"query": "Get market summary for AAPL", "include_thinking": true}'
```

**Stop services when done:**
```bash
make docker-down
```

**Clean everything (removes data):**
```bash
make docker-clean  # Removes containers and volumes
```

### Local Development

```bash
# Install dependencies
make install

# Setup database
make setup-db

# Seed database
make seed-db

# Run server
make run
```

## 📚 Features

- **MCP Tools**: Query transactions, analyze risk metrics, get market summaries
- **AI Reasoning**: Natural language queries with streaming responses (SSE)
- **RBAC Security**: Role-based access control (Admin, Analyst, Viewer)
- **Observability**: Structured logging, Prometheus metrics, Grafana dashboards
- **Docker Support**: One-command deployment with Docker Compose
- **OpenAPI Documentation**: Auto-generated API docs with Swagger UI

## 📖 API Documentation

### Interactive Documentation

The server provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
  - Interactive API explorer
  - Try out endpoints directly
  - View request/response schemas

- **ReDoc**: http://localhost:8000/redoc
  - Clean, readable API documentation
  - Searchable endpoint reference

### OpenAPI Specification

Access the OpenAPI 3.0 specification:

```bash
# JSON format
curl http://localhost:8000/openapi.json

# Download for import into Postman/Insomnia
curl http://localhost:8000/openapi.json -o openapi.json
```

### API Endpoints

#### Reasoning Endpoint
```bash
POST /api/v1/reasoning
Content-Type: application/json
Authorization: Bearer <token>

{
  "query": "Analyze high-risk transactions from last week",
  "include_thinking": true
}
```

#### MCP Protocol Endpoint
```bash
POST /api/v1/mcp
Content-Type: application/json
Authorization: Bearer <token>

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

#### Metrics Endpoint
```bash
GET /api/v1/metrics
# Returns Prometheus-compatible metrics
```

See [API Documentation](docs/api_documentation.md) for complete details.

## 🛠️ Available Make Commands

```bash
# Docker Compose
make docker-up          # Start all services
make docker-down       # Stop all services
make docker-logs       # View app logs
make docker-restart    # Restart services
make docker-build      # Rebuild images
make docker-clean      # Clean everything
make docker-ps        # Show status
make docker-seed       # Run seed script
make docker-token      # Generate admin token

# Development
make install           # Install dependencies
make run               # Run server locally
make seed-db           # Seed database
make setup-db          # Create tables

# Testing
make test              # Run all tests
make test-cov          # Run with coverage
make test-html         # Generate HTML coverage

# Maintenance
make clean             # Clean generated files
make help              # Show all commands
```

## 🔐 Authentication

All API endpoints require JWT authentication:

```bash
# Get admin token (in Docker)
make docker-token

# Or generate locally
python scripts/generate_admin_token.py

# Use in requests
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/reasoning
```

## 📊 Architecture

```
┌─────────────┐
│   Clients   │ (Claude Desktop, API Clients, Web)
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   FastAPI Application   │
│  - /api/v1/reasoning    │
│  - /api/v1/mcp          │
│  - /api/v1/metrics       │
│  - /docs (Swagger)      │
└──────┬──────────────────┘
       │
┌──────▼──────────────┐
│  Service Layer      │
│  - Orchestrator      │
│  - Risk Analyzer     │
│  - Streaming         │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│   MCP Tools Layer   │
│  - query_transactions│
│  - analyze_risk     │
│  - get_market_summary│
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│   Database Layer    │
│   PostgreSQL        │
└─────────────────────┘
```

See [Architecture Documentation](docs/architecture.md) for details.

## 📁 Project Structure

```
cortx/
├── src/
│   ├── api/              # FastAPI routes and schemas
│   ├── auth/             # JWT and RBAC
│   ├── database/         # Models, queries, connection
│   ├── mcp/              # MCP tools and server
│   ├── services/         # Business logic
│   ├── observability/    # Logging, metrics, tracing
│   └── config/           # Settings
├── tests/                # Test suite
├── docs/                 # Documentation
├── alembic/              # Database migrations
├── docker-compose.yml    # Docker setup
├── Dockerfile            # Container image
└── Makefile             # Development commands
```

## 🔧 Configuration

Create a `.env` file (optional):

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/financial_mcp

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production

# Claude API (optional - uses mock orchestrator if not set)
CLAUDE_API_KEY=your_claude_api_key_here

# Logging
LOG_FILE=logs/app.log
DEBUG=True
```

## 📖 Documentation

- [Setup Guide](docs/setup_guide.md) - Complete setup instructions
- [API Documentation](docs/api_documentation.md) - API reference
- [Architecture](docs/architecture.md) - System architecture
- [Security Model](docs/security_model.md) - Authentication & RBAC
- [Observability](docs/OBSERVABILITY.md) - Logging, metrics, tracing
- [Design Decisions](docs/design_decisions.md) - Architectural choices

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Generate HTML coverage report
make test-html
```

## 🐳 Docker Compose Services

- **PostgreSQL**: Database (port 5432)
- **FastAPI Server**: API server (port 8000)
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Dashboards (port 3000)

## 🔒 Security

- JWT-based authentication
- Role-based access control (RBAC)
- Permission-based tool access
- Input validation
- SQL injection protection (SQLAlchemy ORM)

See [Security Model](docs/security_model.md) for details.

## 📈 Observability

- **Structured Logging**: JSON format with request IDs
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: Request ID propagation
- **Dashboards**: Pre-configured Grafana dashboards

See [Observability Guide](docs/OBSERVABILITY.md) for details.

## 🚀 Deployment

### Docker Compose (Recommended)

```bash
make docker-up
```

### Manual Deployment

1. Install dependencies: `make install`
2. Setup database: `make setup-db`
3. Seed data: `make seed-db`
4. Run server: `make run`

See [Setup Guide](docs/setup_guide.md) for detailed instructions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests: `make test`
6. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Support

- Check [Documentation](docs/) for detailed guides
- Review [API Documentation](http://localhost:8000/docs) for endpoint details
- See [Troubleshooting](docs/setup_guide.md#troubleshooting) for common issues

## 🎯 Key Features

✅ **MCP Protocol Support** - Full MCP protocol implementation  
✅ **AI Reasoning** - Natural language query processing with streaming  
✅ **RBAC** - Fine-grained access control  
✅ **Observability** - Full metrics, logging, and tracing  
✅ **Docker** - One-command deployment  
✅ **OpenAPI** - Auto-generated interactive documentation  
✅ **Testing** - Comprehensive test suite with >70% coverage  
✅ **Production Ready** - Error handling, validation, security  

---

**Built with**: FastAPI, PostgreSQL, SQLAlchemy, Claude API, Prometheus, Grafana
# cortx
