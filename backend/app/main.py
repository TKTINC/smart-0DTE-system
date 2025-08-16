"""
Smart-0DTE-System Main Application

This module initializes the FastAPI application with all necessary middleware,
routers, and background tasks for the Smart-0DTE-System.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.core.redis_client import init_redis
from app.core.influxdb_client import init_influxdb
from app.core.logging_config import setup_logging
from app.api.v1.api import api_router
from app.api.v1.readiness import router as readiness_router
from app.services.market_data_service import MarketDataService
from app.services.signal_service import SignalService
from app.services.risk_service import RiskService
from app.core.exceptions import (
    CustomException,
    custom_exception_handler,
    validation_exception_handler,
    http_exception_handler
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global service instances
market_data_service: MarketDataService = None
signal_service: SignalService = None
risk_service: RiskService = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Smart-0DTE-System...")
    
    try:
        # Initialize databases
        await init_db()
        await init_redis()
        await init_influxdb()
        
        # Initialize services
        global market_data_service, signal_service, risk_service
        market_data_service = MarketDataService()
        signal_service = SignalService()
        risk_service = RiskService()
        
        # Start background tasks
        asyncio.create_task(market_data_service.start_real_time_feed())
        asyncio.create_task(signal_service.start_signal_generation())
        asyncio.create_task(risk_service.start_risk_monitoring())
        
        logger.info("Smart-0DTE-System started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart-0DTE-System...")
    
    try:
        # Stop services
        if market_data_service:
            await market_data_service.stop()
        if signal_service:
            await signal_service.stop()
        if risk_service:
            await risk_service.stop()
            
        logger.info("Smart-0DTE-System shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Smart-0DTE-System API",
    description="Advanced 0DTE Options Trading System with Real-time Intelligence",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Add exception handlers
app.add_exception_handler(CustomException, custom_exception_handler)
app.add_exception_handler(422, validation_exception_handler)
app.add_exception_handler(Exception, http_exception_handler)

# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = asyncio.get_event_loop().time()
    
    response = await call_next(request)
    
    process_time = asyncio.get_event_loop().time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response

# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(readiness_router)  # No prefix for /readyz and /livez

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "connected",
            "redis": "connected",
            "influxdb": "connected",
            "market_data": "active" if market_data_service else "inactive",
            "signals": "active" if signal_service else "inactive",
            "risk_management": "active" if risk_service else "inactive"
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic system information."""
    return {
        "message": "Smart-0DTE-System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )

