"""
FastAPI application initialization
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import reasoning, metrics, mcp
from src.config.settings import settings
from src.observability.logging import setup_logging
from src.database.connection import database

# Setup structured logging
setup_logging(
    level="INFO" if not settings.DEBUG else "DEBUG",
    log_file=settings.LOG_FILE
)

app = FastAPI(
    title="Financial MCP Server",
    description="""
    A production-ready Financial MCP (Model Context Protocol) server with AI-powered reasoning capabilities.
    
    ## Features
    
    * **MCP Tools**: Query transactions, analyze risk metrics, get market summaries
    * **AI Reasoning**: Natural language queries with streaming responses (SSE)
    * **RBAC Security**: Role-based access control (Admin, Analyst, Viewer)
    * **Observability**: Structured logging, Prometheus metrics, Grafana dashboards
    
    ## Authentication
    
    All endpoints require JWT authentication via the `Authorization` header:
    
    ```
    Authorization: Bearer <jwt-token>
    ```
    
    Generate an admin token using:
    ```bash
    make docker-token
    # or
    python scripts/generate_admin_token.py
    ```
    
    ## API Endpoints
    
    * `/api/v1/reasoning` - Streaming reasoning endpoint (SSE)
    * `/api/v1/mcp` - MCP protocol endpoint (JSON-RPC 2.0)
    * `/api/v1/metrics` - Prometheus metrics
    * `/health` - Health check
    
    ## Documentation
    
    * Swagger UI: `/docs` (interactive API explorer)
    * ReDoc: `/redoc` (readable documentation)
    * OpenAPI JSON: `/openapi.json`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "reasoning",
            "description": "AI-powered reasoning with streaming responses"
        },
        {
            "name": "mcp",
            "description": "MCP protocol endpoints (JSON-RPC 2.0)"
        },
        {
            "name": "metrics",
            "description": "Prometheus-compatible metrics"
        }
    ]
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    database.initialize(
        database_url=settings.DATABASE_URL,
        echo=settings.DB_ECHO
    )
    print("✅ Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on application shutdown"""
    database.close()
    print("✅ Database connections closed")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with versioning
app.include_router(
    reasoning.router,
    prefix="/api/v1",
    tags=["reasoning"]
)

app.include_router(
    metrics.router,
    prefix="/api/v1",
    tags=["metrics"]
)

app.include_router(
    mcp.router,
    prefix="/api/v1",
    tags=["mcp"]
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Financial MCP Server API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_version": "v1",
        "mcp_endpoint": "/api/v1/mcp"
    }
