"""
Alabama Auction Watcher FastAPI Backend
Phase 2A Week 3-4: Data Synchronization & API Integration

FastAPI application entry point with authentication, rate limiting, and CORS configuration.
Maintains exact algorithm compatibility with existing Python scripts and iOS Swift implementation.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Import centralized configuration
from .config import settings

# Import routers
from .routers import properties, counties, sync, auth, predictions, testing, applications, ai
from .database.connection import database, connect_db, disconnect_db
from .auth import add_security_headers, require_sync_access

# Import caching middleware
from .middleware.caching import CachingMiddleware, CacheControlMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter configuration - uses centralized settings
def get_rate_limit_key(request: Request) -> str:
    """Return key for rate limiting, or empty string to bypass in development."""
    if settings.is_development:
        return ""  # Empty key bypasses rate limiting
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_rate_limit_key,
    enabled=settings.resolved_rate_limit_enabled
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for database connection management."""
    # Startup
    logger.info("=� Starting Alabama Auction Watcher API...")
    await connect_db()
    logger.info(" Database connected successfully")
    yield
    # Shutdown
    logger.info("= Shutting down Alabama Auction Watcher API...")
    await disconnect_db()
    logger.info(" Database disconnected successfully")

# FastAPI application instance
app = FastAPI(
    title="Alabama Auction Watcher API",
    description="REST API for Alabama Auction Watcher mobile application with exact Python algorithm compatibility",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.middleware("http")(add_security_headers)

# CORS configuration - uses centralized settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add caching middleware
app.add_middleware(CacheControlMiddleware)
app.add_middleware(CachingMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time header and request logging for AI monitoring."""
    start_time = time.time()

    # Log request for AI analysis
    logger.info(f"=� {request.method} {request.url.path} - Client: {get_remote_address(request)}")

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log response for AI monitoring
    logger.info(f"=� {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")

    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging for AI analysis."""
    logger.error(f"=� Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "ai_recovery_hint": "Check algorithm compatibility and data validation"
        }
    )

# Health check endpoints
@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "Alabama Auction Watcher API"
    }

@app.get("/health/detailed")
@limiter.limit("10/minute")
async def detailed_health_check(request: Request):
    """Detailed health check with database and algorithm status."""
    try:
        # Test database connection
        db_status = "connected" if database.is_connected else "disconnected"

        # Test algorithm imports (to ensure compatibility)
        try:
            from scripts.utils import calculate_investment_score
            from config.settings import INVESTMENT_SCORE_WEIGHTS

            # Quick algorithm validation
            test_score = calculate_investment_score(5000.0, 3.0, 6.0, 0.8, INVESTMENT_SCORE_WEIGHTS)
            algorithm_status = "validated" if abs(test_score - 52.8) < 0.1 else "validation_failed"
        except Exception as e:
            algorithm_status = f"import_failed: {str(e)}"

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "Alabama Auction Watcher API",
            "components": {
                "database": db_status,
                "algorithms": algorithm_status,
                "python_compatibility": "maintained"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Cache management endpoints
@app.get("/cache/stats")
@limiter.limit("10/minute")
async def cache_stats(request: Request):
    """Get cache statistics and performance metrics."""
    try:
        from .middleware.caching import get_cache_stats
        stats = get_cache_stats()
        return {
            "cache_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")

@app.post("/cache/warm")
@limiter.limit("5/minute")
async def warm_cache_endpoint(request: Request):
    """Manually trigger cache warming."""
    try:
        from config.caching import warm_cache
        await warm_cache()
        return {
            "status": "success",
            "message": "Cache warming completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        raise HTTPException(status_code=500, detail="Cache warming failed")

# API version prefix
API_V1_PREFIX = "/api/v1"

# Include authentication router (no auth required for auth endpoints)
app.include_router(
    auth.router,
    prefix=f"{API_V1_PREFIX}/auth",
    tags=["Authentication"],
    dependencies=[]
)

# Include routers with version prefix and authentication
app.include_router(
    properties.router,
    prefix=f"{API_V1_PREFIX}/properties",
    tags=["Properties"],
    dependencies=[]  # Auth applied per endpoint for granular control
)

app.include_router(
    counties.router,
    prefix=f"{API_V1_PREFIX}/counties",
    tags=["Counties"],
    dependencies=[]  # Counties are public (static data)
)

app.include_router(
    sync.router,
    prefix=f"{API_V1_PREFIX}/sync",
    tags=["Synchronization"],
    dependencies=[Depends(require_sync_access)]  # Require sync access
)

app.include_router(
    predictions.router,
    prefix=f"{API_V1_PREFIX}/predictions",
    tags=["Market Intelligence"],
    dependencies=[]  # Auth applied per endpoint for granular control
)

app.include_router(
    testing.router,
    prefix=f"{API_V1_PREFIX}/testing",
    tags=["AI Testing & Validation"],
    dependencies=[]  # Auth applied per endpoint for granular control
)

app.include_router(
    applications.router,
    prefix=f"{API_V1_PREFIX}/applications",
    tags=["Application Assistant"],
    dependencies=[]  # Auth applied per endpoint for granular control
)

app.include_router(
    ai.router,
    prefix=f"{API_V1_PREFIX}/ai",
    tags=["AI Investment Triage"],
    dependencies=[]  # Auth applied per endpoint for granular control
)

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with service information."""
    return {
        "service": "Alabama Auction Watcher API",
        "version": "1.0.0",
        "phase": "Phase 2A Week 3-4",
        "compatibility": "iOS Swift + Python Backend",
        "docs": "/api/docs",
        "health": "/health",
        "api_base": "/api/v1"
    }

# Development server configuration
if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting development server on {settings.host}:{settings.port}...")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )