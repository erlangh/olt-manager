"""
Main FastAPI application for OLT Management System.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Import database components
from .database.connection import database_manager
from .database.config import get_database_config

# Import API routers
from .api.olt import router as olt_router
from .api.ont import router as ont_router
from .api.monitoring import router as monitoring_router
from .api.auth import router as auth_router
from .api.users import router as users_router
from .api.websocket import router as websocket_router

# Import services
from .services.monitoring_service import monitoring_service
from .services.websocket_service import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} - "
            f"Process time: {process_time:.4f}s"
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    
    logger.info("Starting OLT Management System...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        await database_manager.initialize()
        logger.info("Database initialized successfully")
        
        # Start monitoring service
        logger.info("Starting monitoring service...")
        await monitoring_service.start()
        logger.info("Monitoring service started successfully")
        
        # Application is ready
        logger.info("OLT Management System started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down OLT Management System...")
        
        try:
            # Stop monitoring service
            if monitoring_service.running:
                await monitoring_service.stop()
                logger.info("Monitoring service stopped")
            
            # Close database connections
            await database_manager.close_all_connections()
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("OLT Management System shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="OLT Management System",
    description="Comprehensive OLT and ONT management system with SNMP integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)


# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(olt_router, prefix="/api/v1")
app.include_router(ont_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation error",
            "details": exc.errors(),
            "status_code": 422
        }
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions."""
    
    logger.error(f"Starlette HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    
    return {
        "message": "OLT Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    try:
        # Check database connection
        db_healthy = await database_manager.health_check()
        
        # Check monitoring service
        monitoring_stats = monitoring_service.get_service_stats()
        monitoring_healthy = monitoring_stats["running"]
        
        # Overall health
        healthy = db_healthy and monitoring_healthy
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "monitoring": "healthy" if monitoring_healthy else "unhealthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


# API information endpoint
@app.get("/api/v1/info")
async def api_info():
    """Get API information and statistics."""
    
    try:
        # Get database config
        db_config = get_database_config()
        
        # Get monitoring stats
        monitoring_stats = monitoring_service.get_service_stats()
        
        # Get WebSocket stats
        websocket_stats = {
            "active_connections": len(websocket_manager.active_connections),
            "total_connections": websocket_manager.connection_count
        }
        
        return {
            "api_version": "1.0.0",
            "database": {
                "host": db_config.host,
                "port": db_config.port,
                "database": db_config.database,
                "ssl_enabled": db_config.ssl_mode != "disable"
            },
            "monitoring": monitoring_stats,
            "websocket": websocket_stats,
            "endpoints": {
                "authentication": "/api/v1/auth",
                "users": "/api/v1/users",
                "olts": "/api/v1/olts",
                "onts": "/api/v1/onts",
                "monitoring": "/api/v1/monitoring",
                "websocket": "/api/v1/ws"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get API info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API information"
        )

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_config=log_config,
        access_log=True
    )