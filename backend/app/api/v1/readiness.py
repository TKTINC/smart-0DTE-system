"""
Readiness endpoint for deployment health checks.
Checks all critical dependencies before marking the service as ready.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.influxdb_client import to_rfc3339
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/readyz")
async def readiness_check(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive readiness check for deployment.
    
    Checks:
    - Database connectivity and basic query
    - Redis connectivity and basic operations
    - InfluxDB connectivity (if enabled)
    - Critical configuration validation
    
    Returns 200 if all checks pass, 503 if any fail.
    """
    checks = {}
    all_healthy = True
    
    # Database check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = {"status": "healthy", "message": "Database connection OK"}
        logger.debug("Database readiness check passed")
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}
        all_healthy = False
        logger.error(f"Database readiness check failed: {e}")
    
    # Redis check
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        
        # Test basic operations
        test_key = "readiness_check"
        await redis_client.set(test_key, "ok", ex=10)
        value = await redis_client.get(test_key)
        await redis_client.delete(test_key)
        
        if value == "ok":
            checks["redis"] = {"status": "healthy", "message": "Redis connection and operations OK"}
            logger.debug("Redis readiness check passed")
        else:
            checks["redis"] = {"status": "unhealthy", "message": "Redis operations failed"}
            all_healthy = False
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "message": f"Redis error: {str(e)}"}
        all_healthy = False
        logger.error(f"Redis readiness check failed: {e}")
    
    # InfluxDB check (if enabled)
    settings = get_settings()
    if hasattr(settings, 'INFLUXDB_ENABLED') and settings.INFLUXDB_ENABLED:
        try:
            from app.core.influxdb_client import get_influxdb_client
            influx_client = get_influxdb_client()
            
            # Simple ping check
            health = influx_client.health()
            if health.status == "pass":
                checks["influxdb"] = {"status": "healthy", "message": "InfluxDB connection OK"}
                logger.debug("InfluxDB readiness check passed")
            else:
                checks["influxdb"] = {"status": "unhealthy", "message": f"InfluxDB health: {health.status}"}
                all_healthy = False
        except Exception as e:
            checks["influxdb"] = {"status": "unhealthy", "message": f"InfluxDB error: {str(e)}"}
            all_healthy = False
            logger.error(f"InfluxDB readiness check failed: {e}")
    else:
        checks["influxdb"] = {"status": "disabled", "message": "InfluxDB not enabled"}
    
    # Configuration validation
    try:
        config_issues = []
        
        # Check critical environment variables
        if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-here":
            config_issues.append("SECRET_KEY not properly configured")
        
        if not settings.DATABASE_URL:
            config_issues.append("DATABASE_URL not configured")
        
        if not settings.REDIS_URL:
            config_issues.append("REDIS_URL not configured")
        
        if config_issues:
            checks["configuration"] = {
                "status": "unhealthy", 
                "message": f"Configuration issues: {', '.join(config_issues)}"
            }
            all_healthy = False
        else:
            checks["configuration"] = {"status": "healthy", "message": "Configuration OK"}
            logger.debug("Configuration readiness check passed")
            
    except Exception as e:
        checks["configuration"] = {"status": "unhealthy", "message": f"Configuration error: {str(e)}"}
        all_healthy = False
        logger.error(f"Configuration readiness check failed: {e}")
    
    # Overall status
    status_code = 200 if all_healthy else 503
    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": "2024-01-01T00:00:00Z",  # Will be replaced with actual timestamp
        "checks": checks,
        "version": getattr(settings, 'APP_VERSION', 'unknown')
    }
    
    # Update timestamp with current time
    from datetime import datetime, timezone
    response["timestamp"] = to_rfc3339(datetime.now(timezone.utc))
    
    if not all_healthy:
        logger.warning(f"Readiness check failed: {response}")
        raise HTTPException(status_code=status_code, detail=response)
    
    logger.info("Readiness check passed - service is ready")
    return response

@router.get("/livez")
async def liveness_check() -> Dict[str, str]:
    """
    Simple liveness check for deployment.
    
    This is a lightweight check that only verifies the service is running
    and can respond to requests. Used by load balancers for basic health.
    """
    from datetime import datetime, timezone
    
    return {
        "status": "alive",
        "timestamp": to_rfc3339(datetime.now(timezone.utc)),
        "service": "smart-0dte-system"
    }

