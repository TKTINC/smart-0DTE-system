"""
Tests for Authentication System

Comprehensive test suite for JWT authentication,
role-based access control, and security utilities.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.core.auth import (
    generate_password_hash,
    verify_password,
    generate_jwt_token,
    decode_jwt_token,
    get_current_user,
    require_permission,
    require_role,
    require_any_role,
    TokenData,
    User,
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    APIKeyAuth,
    create_api_user,
    generate_api_key,
    generate_secure_token,
    constant_time_compare,
    get_client_ip,
    create_rate_limit_key
)
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_generate_password_hash(self):
        """Test password hash generation."""
        password = "test_password_123"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        assert len(hash1) > 50  # bcrypt hashes are long
        assert hash1.startswith('$2b$')  # bcrypt format
    
    def test_verify_password(self):
        """Test password verification."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        
        password_hash = generate_password_hash(password)
        
        # Correct password should verify
        assert verify_password(password, password_hash) is True
        
        # Wrong password should not verify
        assert verify_password(wrong_password, password_hash) is False
    
    def test_password_hash_security(self):
        """Test password hash security properties."""
        password = "test_password"
        
        # Generate multiple hashes
        hashes = [generate_password_hash(password) for _ in range(5)]
        
        # All should be different (salted)
        assert len(set(hashes)) == 5
        
        # All should verify correctly
        for hash_val in hashes:
            assert verify_password(password, hash_val) is True


class TestJWTTokens:
    """Test JWT token functionality."""
    
    def create_test_user(self) -> User:
        """Create a test user."""
        return User(
            id="test_user_123",
            username="testuser",
            email="test@example.com",
            role=UserRole.TRADER,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    def test_generate_jwt_token(self):
        """Test JWT token generation."""
        user = self.create_test_user()
        token_data = generate_jwt_token(user)
        
        # Check token structure
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data
        assert "expires_at" in token_data
        assert "user" in token_data
        
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] == settings.JWT_EXPIRATION_HOURS * 3600
        
        # Check user data
        user_data = token_data["user"]
        assert user_data["id"] == user.id
        assert user_data["username"] == user.username
        assert user_data["role"] == user.role
        assert "permissions" in user_data
    
    def test_decode_jwt_token(self):
        """Test JWT token decoding."""
        user = self.create_test_user()
        token_data = generate_jwt_token(user)
        token = token_data["access_token"]
        
        # Decode token
        decoded = decode_jwt_token(token)
        
        assert isinstance(decoded, TokenData)
        assert decoded.user_id == user.id
        assert decoded.username == user.username
        assert decoded.role == user.role
        assert decoded.permissions == ROLE_PERMISSIONS[user.role]
        assert isinstance(decoded.exp, datetime)
        assert isinstance(decoded.iat, datetime)
        assert decoded.jti is not None
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        # Create expired token
        user = self.create_test_user()
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=1)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": ROLE_PERMISSIONS[user.role],
            "exp": expired_time,
            "iat": expired_time - timedelta(hours=1),
            "jti": "test_jti",
            "type": "access_token"
        }
        
        expired_token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # Should raise exception for expired token
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt_token(expired_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()
    
    def test_invalid_token(self):
        """Test invalid token handling."""
        invalid_tokens = [
            "invalid.token.here",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "",
            "not_a_jwt_at_all"
        ]
        
        for invalid_token in invalid_tokens:
            with pytest.raises(HTTPException) as exc_info:
                decode_jwt_token(invalid_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_with_missing_fields(self):
        """Test token with missing required fields."""
        # Token missing required fields
        incomplete_payload = {
            "sub": "user_123",
            # Missing username, role, etc.
        }
        
        incomplete_token = jwt.encode(
            incomplete_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt_token(incomplete_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail


class TestAuthentication:
    """Test authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful user authentication."""
        user = User(
            id="test_user",
            username="testuser",
            email="test@example.com",
            role=UserRole.TRADER,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        token_data = generate_jwt_token(user)
        token = token_data["access_token"]
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        current_user = await get_current_user(credentials)
        
        assert isinstance(current_user, TokenData)
        assert current_user.user_id == user.id
        assert current_user.username == user.username
        assert current_user.role == user.role
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test authentication with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthorization:
    """Test authorization dependencies."""
    
    def create_token_data(self, role: str) -> TokenData:
        """Create test token data."""
        return TokenData(
            user_id="test_user",
            username="testuser",
            role=role,
            permissions=ROLE_PERMISSIONS[role],
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="test_jti"
        )
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test successful permission check."""
        token_data = self.create_token_data(UserRole.TRADER)
        
        # Mock get_current_user to return our token data
        with patch('app.core.auth.get_current_user', return_value=token_data):
            permission_checker = require_permission(Permission.READ)
            result = await permission_checker()
            
            assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_permission_failure(self):
        """Test failed permission check."""
        token_data = self.create_token_data(UserRole.VIEWER)
        
        with patch('app.core.auth.get_current_user', return_value=token_data):
            permission_checker = require_permission(Permission.EXECUTE)
            
            with pytest.raises(HTTPException) as exc_info:
                await permission_checker()
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Insufficient permissions" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_role_success(self):
        """Test successful role check."""
        token_data = self.create_token_data(UserRole.ADMIN)
        
        with patch('app.core.auth.get_current_user', return_value=token_data):
            role_checker = require_role(UserRole.ADMIN)
            result = await role_checker()
            
            assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_role_failure(self):
        """Test failed role check."""
        token_data = self.create_token_data(UserRole.VIEWER)
        
        with patch('app.core.auth.get_current_user', return_value=token_data):
            role_checker = require_role(UserRole.ADMIN)
            
            with pytest.raises(HTTPException) as exc_info:
                await role_checker()
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Insufficient role" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_any_role_success(self):
        """Test successful multiple role check."""
        token_data = self.create_token_data(UserRole.TRADER)
        
        with patch('app.core.auth.get_current_user', return_value=token_data):
            role_checker = require_any_role([UserRole.ADMIN, UserRole.TRADER])
            result = await role_checker()
            
            assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_any_role_failure(self):
        """Test failed multiple role check."""
        token_data = self.create_token_data(UserRole.VIEWER)
        
        with patch('app.core.auth.get_current_user', return_value=token_data):
            role_checker = require_any_role([UserRole.ADMIN, UserRole.TRADER])
            
            with pytest.raises(HTTPException) as exc_info:
                await role_checker()
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Required one of" in exc_info.value.detail


class TestAPIKeyAuth:
    """Test API key authentication."""
    
    def test_api_key_auth_init(self):
        """Test API key auth initialization."""
        api_auth = APIKeyAuth()
        assert isinstance(api_auth.valid_api_keys, set)
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_success(self):
        """Test successful API key authentication."""
        api_auth = APIKeyAuth()
        test_key = "test_api_key_123"
        api_auth.valid_api_keys.add(test_key)
        
        result = await api_auth.authenticate(test_key)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_failure(self):
        """Test failed API key authentication."""
        api_auth = APIKeyAuth()
        invalid_key = "invalid_key"
        
        result = await api_auth.authenticate(invalid_key)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_api_key_dependency_success(self):
        """Test API key FastAPI dependency success."""
        api_auth = APIKeyAuth()
        test_key = "test_api_key_123"
        api_auth.valid_api_keys.add(test_key)
        
        result = await api_auth(test_key)
        assert result == test_key
    
    @pytest.mark.asyncio
    async def test_api_key_dependency_failure(self):
        """Test API key FastAPI dependency failure."""
        api_auth = APIKeyAuth()
        invalid_key = "invalid_key"
        
        with pytest.raises(HTTPException) as exc_info:
            await api_auth(invalid_key)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid API key" in exc_info.value.detail


class TestUserManagement:
    """Test user management functions."""
    
    def test_create_api_user(self):
        """Test API user creation."""
        username = "test_api_user"
        user = create_api_user(username)
        
        assert isinstance(user, User)
        assert user.username == username
        assert user.role == UserRole.API_USER
        assert user.is_active is True
        assert user.id.startswith("api_")
        assert "@api.smart0dte.com" in user.email
    
    def test_create_api_user_custom_role(self):
        """Test API user creation with custom role."""
        username = "admin_api_user"
        role = UserRole.ADMIN
        user = create_api_user(username, role)
        
        assert user.username == username
        assert user.role == role
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()
        
        assert isinstance(api_key, str)
        assert api_key.startswith("sk_")
        assert len(api_key) > 40  # Should be long and secure
        
        # Generate multiple keys - should be different
        keys = [generate_api_key() for _ in range(5)]
        assert len(set(keys)) == 5


class TestSecurityUtilities:
    """Test security utility functions."""
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Should be different
        assert token1 != token2
        
        # Should be URL-safe
        assert all(c.isalnum() or c in '-_' for c in token1)
        
        # Custom length
        custom_token = generate_secure_token(16)
        # URL-safe base64 encoding makes it longer than input
        assert len(custom_token) >= 16
    
    def test_constant_time_compare(self):
        """Test constant-time string comparison."""
        string1 = "test_string_123"
        string2 = "test_string_123"
        string3 = "different_string"
        
        # Same strings should match
        assert constant_time_compare(string1, string2) is True
        
        # Different strings should not match
        assert constant_time_compare(string1, string3) is False
        
        # Empty strings
        assert constant_time_compare("", "") is True
        assert constant_time_compare("", "not_empty") is False
    
    def test_get_client_ip(self):
        """Test client IP extraction."""
        # Mock request with X-Forwarded-For header
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "192.168.1.1, 10.0.0.1"
        mock_request.client.host = "127.0.0.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"  # First IP from forwarded header
        
        # Mock request without forwarded header
        mock_request.headers.get.return_value = None
        ip = get_client_ip(mock_request)
        assert ip == "127.0.0.1"  # Direct client IP
    
    def test_create_rate_limit_key(self):
        """Test rate limit key creation."""
        identifier = "user_123"
        endpoint = "/api/v1/trading"
        
        key = create_rate_limit_key(identifier, endpoint)
        
        assert key == "rate_limit:user_123:/api/v1/trading"
        assert isinstance(key, str)


class TestRolePermissions:
    """Test role and permission system."""
    
    def test_role_permissions_mapping(self):
        """Test role permissions are properly mapped."""
        # Admin should have all permissions
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.READ in admin_perms
        assert Permission.WRITE in admin_perms
        assert Permission.EXECUTE in admin_perms
        assert Permission.ADMIN in admin_perms
        
        # Trader should have read, write, execute but not admin
        trader_perms = ROLE_PERMISSIONS[UserRole.TRADER]
        assert Permission.READ in trader_perms
        assert Permission.WRITE in trader_perms
        assert Permission.EXECUTE in trader_perms
        assert Permission.ADMIN not in trader_perms
        
        # Viewer should only have read
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER]
        assert Permission.READ in viewer_perms
        assert Permission.WRITE not in viewer_perms
        assert Permission.EXECUTE not in viewer_perms
        assert Permission.ADMIN not in viewer_perms
        
        # API user should have read and write
        api_perms = ROLE_PERMISSIONS[UserRole.API_USER]
        assert Permission.READ in api_perms
        assert Permission.WRITE in api_perms
        assert Permission.EXECUTE not in api_perms
        assert Permission.ADMIN not in api_perms
    
    def test_all_roles_have_permissions(self):
        """Test all roles have defined permissions."""
        roles = [UserRole.ADMIN, UserRole.TRADER, UserRole.VIEWER, UserRole.API_USER]
        
        for role in roles:
            assert role in ROLE_PERMISSIONS
            assert isinstance(ROLE_PERMISSIONS[role], list)
            assert len(ROLE_PERMISSIONS[role]) > 0


if __name__ == "__main__":
    pytest.main([__file__])

