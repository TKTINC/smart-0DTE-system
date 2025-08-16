"""
Rate Limiting Middleware

Implements comprehensive rate limiting with Redis backend,
multiple time windows, and endpoint-specific limits.
"""

import logging
import time
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as redis
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.auth import get_client_ip

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_limits = {
            'per_minute': settings.RATE_LIMIT_PER_MINUTE,
            'per_hour': settings.RATE_LIMIT_PER_HOUR,
            'per_day': settings.RATE_LIMIT_PER_DAY,
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/v1/auth/': {
                'per_minute': settings.AUTH_RATE_LIMIT_PER_MINUTE,
                'per_hour': 100,
                'per_day': 1000,
            },
            '/api/v1/trading/': {
                'per_minute': settings.TRADING_RATE_LIMIT_PER_MINUTE,
                'per_hour': 1000,
                'per_day': 10000,
            },
            '/api/v1/market-data/': {
                'per_minute': settings.MARKET_DATA_RATE_LIMIT_PER_MINUTE,
                'per_hour': 5000,
                'per_day': 50000,
            },
        }
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.RATE_LIMIT_STORAGE_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
            )
            await self.redis_client.ping()
            logger.info("Rate limiter Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to rate limiter Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_endpoint_limits(self, path: str) -> Dict[str, int]:
        """Get rate limits for specific endpoint."""
        for endpoint_prefix, limits in self.endpoint_limits.items():
            if path.startswith(endpoint_prefix):
                return limits
        return self.default_limits
    
    async def _check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check rate limit using sliding window algorithm.
        
        Args:
            key: Redis key for the rate limit
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            tuple: (is_allowed, rate_limit_info)
        """
        now = time.time()
        pipeline = self.redis_client.pipeline()
        
        # Remove expired entries
        pipeline.zremrangebyscore(key, 0, now - window_seconds)
        
        # Count current requests
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(now): now})
        
        # Set expiration
        pipeline.expire(key, window_seconds)
        
        results = await pipeline.execute()
        current_count = results[1]
        
        # Calculate rate limit info
        reset_time = now + window_seconds
        remaining = max(0, limit - current_count - 1)
        
        rate_limit_info = {
            'limit': limit,
            'remaining': remaining,
            'reset': int(reset_time),
            'reset_time': datetime.fromtimestamp(reset_time).isoformat(),
            'window_seconds': window_seconds,
        }
        
        is_allowed = current_count < limit
        
        if not is_allowed:
            # Remove the request we just added since it's not allowed
            await self.redis_client.zrem(key, str(now))
        
        return is_allowed, rate_limit_info
    
    async def check_limits(
        self,
        identifier: str,
        path: str
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check all rate limits for an identifier and path.
        
        Args:
            identifier: Client identifier (IP, user ID, API key)
            path: Request path
            
        Returns:
            tuple: (is_allowed, combined_rate_limit_info)
        """
        if not self.redis_client:
            # If Redis is not available, allow the request
            logger.warning("Rate limiter Redis not available, allowing request")
            return True, {}
        
        limits = self._get_endpoint_limits(path)
        
        # Check each time window
        checks = [
            ('per_minute', limits['per_minute'], 60),
            ('per_hour', limits['per_hour'], 3600),
            ('per_day', limits['per_day'], 86400),
        ]
        
        combined_info = {}
        
        for window_name, limit, window_seconds in checks:
            key = f"rate_limit:{identifier}:{path}:{window_name}"
            
            is_allowed, rate_info = await self._check_rate_limit(
                key, limit, window_seconds
            )
            
            combined_info[window_name] = rate_info
            
            if not is_allowed:
                return False, combined_info
        
        return True, combined_info
    
    async def get_rate_limit_status(
        self,
        identifier: str,
        path: str
    ) -> Dict[str, any]:
        """Get current rate limit status without incrementing counters."""
        if not self.redis_client:
            return {}
        
        limits = self._get_endpoint_limits(path)
        now = time.time()
        
        status = {}
        
        for window_name, limit, window_seconds in [
            ('per_minute', limits['per_minute'], 60),
            ('per_hour', limits['per_hour'], 3600),
            ('per_day', limits['per_day'], 86400),
        ]:
            key = f"rate_limit:{identifier}:{path}:{window_name}"
            
            # Count current requests without modifying
            current_count = await self.redis_client.zcount(
                key, now - window_seconds, now
            )
            
            reset_time = now + window_seconds
            remaining = max(0, limit - current_count)
            
            status[window_name] = {
                'limit': limit,
                'remaining': remaining,
                'reset': int(reset_time),
                'reset_time': datetime.fromtimestamp(reset_time).isoformat(),
                'window_seconds': window_seconds,
            }
        
        return status


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for health checks and static files
        if self._should_skip_rate_limiting(request.url.path):
            await self.app(scope, receive, send)
            return
        
        # Get client identifier
        client_ip = get_client_ip(request)
        user_id = await self._get_user_id(request)
        identifier = user_id or client_ip
        
        # Check rate limits
        try:
            is_allowed, rate_info = await rate_limiter.check_limits(
                identifier, request.url.path
            )
            
            if not is_allowed:
                # Find the most restrictive limit that was exceeded
                exceeded_window = None
                for window_name, info in rate_info.items():
                    if info['remaining'] == 0:
                        exceeded_window = window_name
                        break
                
                response_data = {
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit exceeded for {exceeded_window}.",
                    "rate_limit": rate_info,
                    "retry_after": min(
                        info['reset'] - int(time.time())
                        for info in rate_info.values()
                        if info['remaining'] == 0
                    )
                }
                
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=response_data
                )
                
                # Add rate limit headers
                self._add_rate_limit_headers(response, rate_info)
                
                await response(scope, receive, send)
                return
            
            # Add rate limit headers to successful responses
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    self._add_rate_limit_headers_dict(headers, rate_info)
                    message["headers"] = list(headers.items())
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # If rate limiting fails, allow the request
            await self.app(scope, receive, send)
    
    def _should_skip_rate_limiting(self, path: str) -> bool:
        """Check if path should skip rate limiting."""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static/",
            "/favicon.ico",
        ]
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request if authenticated."""
        try:
            # Try to get user ID from JWT token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # This would require importing auth module
                # For now, return None to use IP-based limiting
                pass
        except Exception:
            pass
        return None
    
    def _add_rate_limit_headers(self, response: JSONResponse, rate_info: Dict):
        """Add rate limit headers to response."""
        if 'per_minute' in rate_info:
            info = rate_info['per_minute']
            response.headers["X-RateLimit-Limit"] = str(info['limit'])
            response.headers["X-RateLimit-Remaining"] = str(info['remaining'])
            response.headers["X-RateLimit-Reset"] = str(info['reset'])
    
    def _add_rate_limit_headers_dict(self, headers: Dict, rate_info: Dict):
        """Add rate limit headers to headers dict."""
        if 'per_minute' in rate_info:
            info = rate_info['per_minute']
            headers[b"x-ratelimit-limit"] = str(info['limit']).encode()
            headers[b"x-ratelimit-remaining"] = str(info['remaining']).encode()
            headers[b"x-ratelimit-reset"] = str(info['reset']).encode()


# Dependency for manual rate limit checking
async def check_rate_limit(request: Request) -> Dict[str, any]:
    """
    FastAPI dependency for manual rate limit checking.
    
    Args:
        request: FastAPI request object
        
    Returns:
        dict: Rate limit information
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_client_ip(request)
    
    is_allowed, rate_info = await rate_limiter.check_limits(
        client_ip, request.url.path
    )
    
    if not is_allowed:
        exceeded_window = None
        for window_name, info in rate_info.items():
            if info['remaining'] == 0:
                exceeded_window = window_name
                break
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit exceeded for {exceeded_window}.",
                "rate_limit": rate_info,
            }
        )
    
    return rate_info

