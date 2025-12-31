# Setup Guide

Complete setup instructions for the Financial MCP Server, including Docker Compose deployment for local development.

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Docker and Docker Compose (for containerized deployment)

## Quick Start with Docker Compose (Recommended)

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd cortx

# Start all services (database, server, Prometheus, Grafana)
docker-compose up -d

# View logs
docker-compose logs -f app
```

The setup automatically:
- Starts PostgreSQL database
- Waits for database to be ready
- Runs database seed script (first time only)
- Starts FastAPI server
- Starts Prometheus and Grafana for observability

Access the services:
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

See [Docker Compose Deployment](#docker-compose-deployment) section for detailed information.

## Local Development Setup (Without Docker)

### 1. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd cortx

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/financial_mcp

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Claude API (optional - if not set, uses mock orchestrator)
CLAUDE_API_KEY=your_claude_api_key_here

# Server Settings
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Logging
LOG_FILE=logs/app.log
```

### 3. Database Setup

```bash
# Initialize database tables
# Database tables are created automatically on startup via src/api/main.py

# Seed with sample data
python -m src.database.seed
```

### 4. Run the Server

```bash
# Using uvicorn directly
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Or using the Makefile
make run

# Or using uvicorn directly (recommended)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`

## Docker Compose Deployment

### Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (optional, defaults provided)

### One-Command Deployment

The project includes a complete `docker-compose.yml` file that sets up everything needed for local development:

```bash
# Start all services (database, server, Prometheus, Grafana)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### What Gets Started

The Docker Compose setup automatically:

1. **PostgreSQL Database** (port 5432)
   - Database: `financial_mcp`
   - User: `financial_user`
   - Password: `financial_password`
   - Health checks ensure database is ready before starting app

2. **FastAPI Server** (port 8000)
   - Automatically runs database seed script on first startup
   - Starts the FastAPI server with auto-reload
   - Connects to PostgreSQL container

3. **Prometheus** (port 9090)
   - Scrapes metrics from FastAPI server
   - Configuration: `docs/prometheus/prometheus.yml`

4. **Grafana** (port 3000)
   - Default credentials: `admin` / `admin`
   - Pre-configured dashboards from `docs/grafana/dashboards/`

### First-Time Setup Flow

When you run `docker-compose up` for the first time:

1. PostgreSQL container starts and initializes database
2. FastAPI container waits for PostgreSQL to be healthy
3. Database seed script runs automatically (`python -m src.database.seed`)
4. FastAPI server starts on port 8000
5. Prometheus and Grafana start for observability

### Access Services

- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Environment Variables

Create a `.env` file in the project root (optional):

```env
# JWT Secret (required for production)
JWT_SECRET_KEY=your-secret-key-change-in-production

# Claude API (optional - uses mock orchestrator if not set)
CLAUDE_API_KEY=your_claude_api_key_here
```

If `.env` is not provided, default values are used for local development.

### Testing with Docker

Once containers are running:

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test reasoning endpoint (get token first)
curl -X POST http://localhost:8000/api/v1/reasoning \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "Get market summary for AAPL", "include_thinking": true}'

# Test MCP endpoint
curl -X POST http://localhost:8000/api/v1/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### Database Persistence

**Important:** Docker volumes persist data between container restarts!

- The `postgres_data` volume stores all database data
- Data remains intact when you restart containers (`docker-compose restart`)
- Data remains intact when you stop and start containers (`docker-compose down` then `docker-compose up`)
- Data is only lost if you explicitly remove the volume (`docker-compose down -v`)

**Seed Script Behavior:**
- The seed script automatically checks if data already exists
- If data exists, it skips seeding (no duplicates)
- If database is empty, it seeds with sample data
- This happens automatically on every container start

### Re-seeding Database

To force re-seed the database (replaces existing data):

```bash
# Option 1: Force re-seed (keeps existing data, adds more)
docker-compose exec app python -m src.database.seed --force

# Option 2: Clean slate (removes all data, then re-seeds)
docker-compose down -v  # Remove volumes
docker-compose up -d     # Start fresh (will auto-seed)
```

**Note:** The seed script now checks if data exists and skips seeding if tables already have data. Use `--force` flag to override this behavior.

### Development Workflow

For active development with code changes:

```bash
# Start in foreground to see logs
docker-compose up

# Or start in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Restart a specific service
docker-compose restart app

# Rebuild after code changes
docker-compose up -d --build app
```

### Troubleshooting

**Database connection issues:**
```bash
# Check if postgres is healthy
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Connect to database directly
docker-compose exec postgres psql -U financial_user -d financial_mcp
```

**Server not starting:**
```bash
# Check app logs
docker-compose logs app

# Check if seed script ran
docker-compose logs app | grep "Database seeding"
```

**Port already in use:**
```bash
# Change ports in docker-compose.yml or stop conflicting services
# For example, if 8000 is in use, change:
# ports:
#   - "8001:8000"  # Use 8001 on host instead
```

## Claude Desktop Configuration

### HTTP MCP Setup

Configure Claude Desktop to connect via HTTP:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**

```json
{
  "mcpServers": {
    "financial-mcp-server": {
      "url": "http://localhost:8000/api/v1/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
      }
    }
  }
}
```

### Generate JWT Token

**For Docker Compose (Recommended):**

The admin JWT token is automatically generated and displayed in the container logs when you start the services:

```bash
# Start services (token will be shown in logs)
docker-compose up -d

# View the token
docker-compose logs app | grep -A 5 "ADMIN JWT TOKEN"
```

**For Local Development (without Docker):**

```bash
# Generate admin token
python scripts/generate_admin_token.py

# Or use the auth utilities directly
python -c "from src.auth.utils import create_admin_token; print(create_admin_token(user_id=1, username='admin'))"
```

**Note:** The token generated in Docker Compose uses a hardcoded secret key (`dev-secret-key-for-local-development-only`) and expires in 1 year for convenience. For production, use a strong random secret key.

## Testing the Setup

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. List MCP Tools

```bash
curl -X POST http://localhost:8000/api/v1/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 3. Test Reasoning Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/reasoning \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "Get market summary for AAPL",
    "include_thinking": true
  }'
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_mcp_tools.py
```

### Database Migrations

Database migrations are handled via Alembic. To set up migrations:

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL in `.env`
- Ensure database exists: `createdb financial_mcp`

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### JWT Token Issues

- Verify JWT_SECRET_KEY matches between token generation and server
- Check token expiration time
- Ensure token includes required claims (user_id, roles)

### Claude API Issues

- If CLAUDE_API_KEY is not set, the system uses MockReasoningOrchestrator
- Mock orchestrator uses query parsing instead of Claude API
- Check API key validity if using Claude API

## Production Deployment

### Environment Variables

Set production environment variables:

```env
DEBUG=False
JWT_SECRET_KEY=<strong-random-secret>
DATABASE_URL=<production-database-url>
CLAUDE_API_KEY=<production-api-key>
```

### Security Checklist

- [ ] Change JWT_SECRET_KEY to strong random value
- [ ] Set DEBUG=False
- [ ] Configure CORS_ORIGINS appropriately
- [ ] Use SSL/TLS for production
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring and alerts

## Next Steps

- See [API Documentation](api_documentation.md) for endpoint details
- See [Security Model](security_model.md) for authentication setup
- See [Architecture](architecture.md) for system overview

