"""
Authentication and Authorization Module

Provides JWT-based authentication, role-based access control,
and security utilities for the Smart-0DTE-System.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import secrets

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer()

# User roles
class UserRole:
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_USER = "api_user"

# Permission levels
class Permission:
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

# Role permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN],
    UserRole.TRADER: [Permission.READ, Permission.WRITE, Permission.EXECUTE],
    UserRole.VIEWER: [Permission.READ],
    UserRole.API_USER: [Permission.READ, Permission.WRITE],
}


class TokenData(BaseModel):
    """Token payload data model."""
    user_id: str
    username: str
    role: str
    permissions: List[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token revocation


class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: str
    role: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


def generate_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_jwt_token(user: User) -> Dict[str, Any]:
    """
    Generate JWT access token for user.
    
    Args:
        user: User object
        
    Returns:
        dict: Token data including access_token, token_type, expires_in
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    # Generate unique JWT ID
    jti = secrets.token_urlsafe(32)
    
    # Create token payload
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "permissions": ROLE_PERMISSIONS.get(user.role, []),
        "exp": expires_at,
        "iat": now,
        "jti": jti,
        "type": "access_token"
    }
    
    # Encode JWT
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRATION_HOURS * 3600,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": ROLE_PERMISSIONS.get(user.role, [])
        }
    }


def decode_jwt_token(token: str) -> TokenData:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Validate required fields
        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")
        permissions = payload.get("permissions", [])
        exp = payload.get("exp")
        iat = payload.get("iat")
        jti = payload.get("jti")
        
        if not all([user_id, username, role, exp, iat, jti]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convert timestamps
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc)
        
        # Check expiration
        if exp_dt < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            permissions=permissions,
            exp=exp_dt,
            iat=iat_dt,
            jti=jti
        )
        
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        TokenData: Current user token data
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        token_data = decode_jwt_token(token)
        
        # TODO: Add token revocation check against Redis blacklist
        # if await is_token_revoked(token_data.jti):
        #     raise HTTPException(status_code=401, detail="Token has been revoked")
        
        return token_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(required_permission: str):
    """
    Dependency factory for permission-based access control.
    
    Args:
        required_permission: Required permission level
        
    Returns:
        Dependency function
    """
    async def permission_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if required_permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
        return current_user
    
    return permission_checker


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required: {required_role}"
            )
        return current_user
    
    return role_checker


def require_any_role(required_roles: List[str]):
    """
    Dependency factory for multiple role access control.
    
    Args:
        required_roles: List of acceptable roles
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required one of: {required_roles}"
            )
        return current_user
    
    return role_checker


# Convenience dependencies
RequireAdmin = Depends(require_role(UserRole.ADMIN))
RequireTrader = Depends(require_any_role([UserRole.ADMIN, UserRole.TRADER]))
RequireViewer = Depends(require_any_role([UserRole.ADMIN, UserRole.TRADER, UserRole.VIEWER]))

RequireRead = Depends(require_permission(Permission.READ))
RequireWrite = Depends(require_permission(Permission.WRITE))
RequireExecute = Depends(require_permission(Permission.EXECUTE))
RequireAdminPermission = Depends(require_permission(Permission.ADMIN))


class APIKeyAuth:
    """API Key authentication for external integrations."""
    
    def __init__(self):
        self.valid_api_keys = set()
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load valid API keys from configuration."""
        # TODO: Load from database or secure configuration
        api_keys = getattr(settings, 'VALID_API_KEYS', [])
        self.valid_api_keys = set(api_keys)
    
    async def authenticate(self, api_key: str) -> bool:
        """
        Authenticate API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            bool: True if valid
        """
        return api_key in self.valid_api_keys
    
    async def __call__(self, api_key: str) -> str:
        """
        FastAPI dependency for API key authentication.
        
        Args:
            api_key: API key from header
            
        Returns:
            str: Validated API key
            
        Raises:
            HTTPException: If API key is invalid
        """
        if not await self.authenticate(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        return api_key


# Global API key authenticator
api_key_auth = APIKeyAuth()


def create_api_user(username: str, role: str = UserRole.API_USER) -> User:
    """
    Create API user for external integrations.
    
    Args:
        username: API username
        role: User role
        
    Returns:
        User: Created user object
    """
    return User(
        id=f"api_{secrets.token_urlsafe(16)}",
        username=username,
        email=f"{username}@api.smart0dte.com",
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


def generate_api_key() -> str:
    """
    Generate secure API key.
    
    Returns:
        str: Generated API key
    """
    return f"sk_{secrets.token_urlsafe(32)}"


# Security utilities
def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return secrets.compare_digest(a, b)


# Rate limiting helpers (to be used with slowapi)
def get_client_ip(request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def create_rate_limit_key(identifier: str, endpoint: str) -> str:
    """Create rate limiting key."""
    return f"rate_limit:{identifier}:{endpoint}"

