"""
Logging Middleware

Comprehensive request/response logging with structured logging,
performance metrics, and security event tracking.
"""

import logging
import time
import json
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime, timezone

from app.core.config import settings
from app.core.auth import get_client_ip

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware:
    """Middleware for comprehensive request/response logging."""
    
    def __init__(self, app):
        self.app = app
        self.sensitive_headers = {
            'authorization', 'cookie', 'x-api-key', 'x-auth-token'
        }
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'auth'
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Extract request information
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        # Log request start
        request_log = {
            "event": "request_start",
            "request_id": request_id,
            "method": method,
            "path": path,
            "query_params": query_params,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "headers": self._sanitize_headers(dict(request.headers)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add request body for POST/PUT/PATCH requests (if not too large)
        if method in ["POST", "PUT", "PATCH"]:
            try:
                content_length = int(request.headers.get("content-length", 0))
                if content_length > 0 and content_length < 10000:  # Max 10KB
                    body = await request.body()
                    if body:
                        try:
                            # Try to parse as JSON
                            body_data = json.loads(body.decode())
                            request_log["body"] = self._sanitize_body(body_data)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            request_log["body"] = "<binary_or_invalid_json>"
            except Exception as e:
                logger.warning("Failed to read request body", error=str(e))
        
        logger.info("HTTP request started", **request_log)
        
        # Store request info in scope for access by other middleware/handlers
        scope["request_id"] = request_id
        scope["start_time"] = start_time
        
        # Capture response
        response_body = b""
        response_status = 200
        response_headers = {}
        
        async def send_wrapper(message):
            nonlocal response_body, response_status, response_headers
            
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = dict(message.get("headers", []))
                
                # Add request ID to response headers
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", request_id.encode()))
            
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_body += body
                
                # Log response when complete
                if not message.get("more_body", False):
                    await self._log_response(
                        request_log, response_status, response_headers,
                        response_body, start_time
                    )
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Log unhandled exceptions
            duration = time.time() - start_time
            
            logger.error(
                "Unhandled exception in request",
                request_id=request_id,
                method=method,
                path=path,
                client_ip=client_ip,
                duration=duration,
                error=str(e),
                exception_type=type(e).__name__
            )
            raise
    
    async def _log_response(
        self,
        request_log: Dict[str, Any],
        status: int,
        headers: Dict,
        body: bytes,
        start_time: float
    ):
        """Log response information."""
        duration = time.time() - start_time
        
        response_log = {
            "event": "request_complete",
            "request_id": request_log["request_id"],
            "method": request_log["method"],
            "path": request_log["path"],
            "client_ip": request_log["client_ip"],
            "status_code": status,
            "duration_ms": round(duration * 1000, 2),
            "response_size": len(body),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add response body for errors or if small enough
        if status >= 400 or (len(body) < 1000 and len(body) > 0):
            try:
                body_text = body.decode('utf-8')
                try:
                    # Try to parse as JSON
                    body_data = json.loads(body_text)
                    response_log["response_body"] = body_data
                except json.JSONDecodeError:
                    response_log["response_body"] = body_text
            except UnicodeDecodeError:
                response_log["response_body"] = "<binary_data>"
        
        # Determine log level based on status code and duration
        if status >= 500:
            log_level = "error"
        elif status >= 400:
            log_level = "warning"
        elif duration > 5.0:  # Slow requests
            log_level = "warning"
            response_log["slow_request"] = True
        else:
            log_level = "info"
        
        # Log performance metrics
        if duration > 1.0:
            response_log["performance_warning"] = True
        
        # Log security events
        if status == 401:
            response_log["security_event"] = "unauthorized_access"
        elif status == 403:
            response_log["security_event"] = "forbidden_access"
        elif status == 429:
            response_log["security_event"] = "rate_limit_exceeded"
        
        getattr(logger, log_level)("HTTP request completed", **response_log)
        
        # Log additional metrics for monitoring
        self._log_metrics(response_log)
    
    def _log_metrics(self, response_log: Dict[str, Any]):
        """Log metrics for monitoring systems."""
        metrics_log = {
            "event": "request_metrics",
            "method": response_log["method"],
            "path": response_log["path"],
            "status_code": response_log["status_code"],
            "duration_ms": response_log["duration_ms"],
            "response_size": response_log["response_size"],
            "timestamp": response_log["timestamp"],
        }
        
        # Add performance classification
        duration_ms = response_log["duration_ms"]
        if duration_ms < 100:
            metrics_log["performance_class"] = "fast"
        elif duration_ms < 500:
            metrics_log["performance_class"] = "normal"
        elif duration_ms < 2000:
            metrics_log["performance_class"] = "slow"
        else:
            metrics_log["performance_class"] = "very_slow"
        
        logger.info("Request metrics", **metrics_log)
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive information from headers."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_body(self, body: Any) -> Any:
        """Remove sensitive information from request body."""
        if isinstance(body, dict):
            sanitized = {}
            for key, value in body.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    sanitized[key] = "<redacted>"
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_body(value)
                elif isinstance(value, list):
                    sanitized[key] = [
                        self._sanitize_body(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    sanitized[key] = value
            return sanitized
        elif isinstance(body, list):
            return [
                self._sanitize_body(item) if isinstance(item, dict) else item
                for item in body
            ]
        else:
            return body


class SecurityLoggingMiddleware:
    """Middleware for security event logging."""
    
    def __init__(self, app):
        self.app = app
        self.suspicious_patterns = [
            'script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
            '../', '..\\', '/etc/passwd', '/etc/shadow', 'cmd.exe',
            'powershell', 'bash', 'sh', 'eval(', 'exec(',
            'union select', 'drop table', 'insert into', 'delete from'
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Check for suspicious patterns
        await self._check_security_threats(request)
        
        await self.app(scope, receive, send)
    
    async def _check_security_threats(self, request: Request):
        """Check for potential security threats."""
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        query_string = str(request.query_params)
        
        threats_detected = []
        
        # Check for suspicious patterns in URL and query parameters
        for pattern in self.suspicious_patterns:
            if pattern.lower() in path.lower() or pattern.lower() in query_string.lower():
                threats_detected.append(f"suspicious_pattern_{pattern}")
        
        # Check for SQL injection patterns
        sql_patterns = ['union select', 'drop table', 'insert into', 'delete from', "' or '1'='1"]
        for pattern in sql_patterns:
            if pattern in query_string.lower():
                threats_detected.append("potential_sql_injection")
                break
        
        # Check for XSS patterns
        xss_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
        for pattern in xss_patterns:
            if pattern in query_string.lower():
                threats_detected.append("potential_xss")
                break
        
        # Check for path traversal
        if '../' in path or '..\\' in path:
            threats_detected.append("path_traversal")
        
        # Check for suspicious user agents
        suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zap']
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            threats_detected.append("suspicious_user_agent")
        
        # Log security threats
        if threats_detected:
            logger.warning(
                "Security threat detected",
                client_ip=client_ip,
                user_agent=user_agent,
                path=path,
                query_string=query_string,
                threats=threats_detected,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event="security_threat"
            )


# Utility functions for manual logging
def log_business_event(event_type: str, **kwargs):
    """Log business logic events."""
    logger.info(
        "Business event",
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **kwargs
    )


def log_security_event(event_type: str, **kwargs):
    """Log security events."""
    logger.warning(
        "Security event",
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **kwargs
    )


def log_performance_event(event_type: str, duration_ms: float, **kwargs):
    """Log performance events."""
    log_level = "warning" if duration_ms > 1000 else "info"
    getattr(logger, log_level)(
        "Performance event",
        event_type=event_type,
        duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **kwargs
    )


def log_error_event(error: Exception, context: Dict[str, Any] = None):
    """Log error events with context."""
    logger.error(
        "Error event",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

