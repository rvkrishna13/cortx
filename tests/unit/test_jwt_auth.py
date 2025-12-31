"""
Unit tests for JWT authentication
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from jose import JWTError
from src.auth.jwt_auth import (
    create_access_token,
    decode_token,
    validate_token,
    extract_user_from_token
)
from src.utils.exceptions import ValidationError
from src.config.settings import settings


class TestCreateAccessToken:
    """Tests for create_access_token function"""
    
    def test_create_access_token_success(self):
        """Test successful token creation"""
        data = {
            "user_id": 1,
            "username": "test_user",
            "roles": ["admin"]
        }
        
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expires_delta(self):
        """Test token creation with custom expiration"""
        data = {"user_id": 1, "username": "test_user"}
        expires_delta = timedelta(minutes=30)
        
        token = create_access_token(data, expires_delta=expires_delta)
        
        assert token is not None
    
    def test_create_access_token_with_default_expiration(self):
        """Test token creation with default expiration from settings"""
        data = {"user_id": 1, "username": "test_user"}
        
        token = create_access_token(data)
        
        assert token is not None
        # Decode to verify expiration
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_access_token_includes_all_data(self):
        """Test that token includes all provided data"""
        data = {
            "user_id": 1,
            "username": "test_user",
            "roles": ["admin", "analyst"],
            "email": "test@example.com"
        }
        
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload["user_id"] == 1
        assert payload["username"] == "test_user"
        assert payload["roles"] == ["admin", "analyst"]
        assert payload["email"] == "test@example.com"


class TestDecodeToken:
    """Tests for decode_token function"""
    
    def test_decode_token_success(self):
        """Test successful token decoding"""
        data = {"user_id": 1, "username": "test_user"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload["user_id"] == 1
        assert payload["username"] == "test_user"
    
    def test_decode_token_invalid_signature(self):
        """Test decoding token with invalid signature"""
        # Create token with correct secret
        data = {"user_id": 1}
        token = create_access_token(data)
        
        # Try to decode with wrong secret by patching settings
        with patch('src.auth.jwt_auth.settings') as mock_settings:
            mock_settings.JWT_SECRET_KEY = "wrong_secret"
            mock_settings.JWT_ALGORITHM = settings.JWT_ALGORITHM
            
            with pytest.raises(ValidationError) as exc_info:
                decode_token(token)
            
            assert "Invalid token" in str(exc_info.value)
    
    def test_decode_token_expired(self):
        """Test decoding expired token"""
        data = {"user_id": 1}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)
        
        # Wait a bit to ensure expiration
        import time
        time.sleep(0.1)
        
        with pytest.raises(ValidationError) as exc_info:
            decode_token(token)
        
        assert "Invalid token" in str(exc_info.value)
    
    def test_decode_token_malformed(self):
        """Test decoding malformed token"""
        with pytest.raises(ValidationError) as exc_info:
            decode_token("not.a.valid.token")
        
        assert "Invalid token" in str(exc_info.value)
    
    def test_decode_token_empty_string(self):
        """Test decoding empty token"""
        with pytest.raises(ValidationError) as exc_info:
            decode_token("")
        
        assert "Invalid token" in str(exc_info.value)
    
    def test_decode_token_jwt_error(self):
        """Test handling of JWTError"""
        with patch('src.auth.jwt_auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = JWTError("JWT error")
            
            with pytest.raises(ValidationError) as exc_info:
                decode_token("some.token")
            
            assert "Invalid token" in str(exc_info.value)
    
    def test_decode_token_unexpected_error(self):
        """Test handling of unexpected errors"""
        with patch('src.auth.jwt_auth.jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Unexpected error")
            
            with pytest.raises(ValidationError) as exc_info:
                decode_token("some.token")
            
            assert "Token validation error" in str(exc_info.value)


class TestValidateToken:
    """Tests for validate_token function"""
    
    def test_validate_token_success(self):
        """Test successful token validation"""
        data = {"user_id": 1, "username": "test_user"}
        token = create_access_token(data)
        
        payload = validate_token(token)
        
        assert payload["user_id"] == 1
        assert payload["username"] == "test_user"
    
    def test_validate_token_with_bearer_prefix(self):
        """Test validation with Bearer prefix"""
        data = {"user_id": 1, "username": "test_user"}
        token = create_access_token(data)
        bearer_token = f"Bearer {token}"
        
        payload = validate_token(bearer_token)
        
        assert payload["user_id"] == 1
    
    def test_validate_token_empty_string(self):
        """Test validation with empty token"""
        with pytest.raises(ValidationError) as exc_info:
            validate_token("")
        
        assert "Token is required" in str(exc_info.value)
    
    def test_validate_token_missing_user_id(self):
        """Test validation with token missing user_id"""
        data = {"username": "test_user"}  # No user_id
        token = create_access_token(data)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_token(token)
        
        assert "Token missing user identifier" in str(exc_info.value)
    
    def test_validate_token_with_sub_instead_of_user_id(self):
        """Test validation with 'sub' field instead of user_id"""
        # JWT 'sub' must be a string
        data = {"sub": "1", "username": "test_user"}
        token = create_access_token(data)
        
        # validate_token should accept 'sub' as user identifier
        payload = validate_token(token)
        
        assert "sub" in payload or "user_id" in payload
        assert payload.get("sub") == "1" or payload.get("user_id") == "1"
    
    def test_validate_token_invalid_token(self):
        """Test validation with invalid token"""
        with pytest.raises(ValidationError) as exc_info:
            validate_token("invalid.token.here")
        
        assert "Invalid token" in str(exc_info.value)


class TestExtractUserFromToken:
    """Tests for extract_user_from_token function"""
    
    def test_extract_user_from_token_success(self):
        """Test successful user extraction"""
        data = {
            "user_id": 1,
            "username": "test_user",
            "roles": ["admin"],
            "email": "test@example.com"
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        assert user_info["user_id"] == 1
        assert user_info["username"] == "test_user"
        assert user_info["roles"] == ["admin"]
        assert user_info["email"] == "test@example.com"
    
    def test_extract_user_from_token_with_sub(self):
        """Test extraction with 'sub' field instead of user_id"""
        # JWT 'sub' must be a string, but extract_user_from_token converts it
        data = {
            "sub": "2",  # String as required by JWT
            "preferred_username": "test_user2",
            "roles": ["analyst"]
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        # extract_user_from_token should handle 'sub' as user_id
        assert user_info["user_id"] == "2"  # May be string or converted
        assert user_info["username"] == "test_user2" or user_info["username"] == ""
    
    def test_extract_user_from_token_string_roles(self):
        """Test extraction with string role (converted to list)"""
        data = {
            "user_id": 3,
            "username": "test_user3",
            "roles": "viewer"  # String instead of list
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        assert user_info["roles"] == ["viewer"]
    
    def test_extract_user_from_token_no_roles(self):
        """Test extraction with no roles field"""
        data = {
            "user_id": 4,
            "username": "test_user4"
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        assert user_info["roles"] == []
    
    def test_extract_user_from_token_invalid_roles_type(self):
        """Test extraction with invalid roles type"""
        data = {
            "user_id": 5,
            "username": "test_user5",
            "roles": 123  # Invalid type
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        assert user_info["roles"] == []
    
    def test_extract_user_from_token_missing_email(self):
        """Test extraction with missing email"""
        data = {
            "user_id": 6,
            "username": "test_user6",
            "roles": ["admin"]
        }
        token = create_access_token(data)
        
        user_info = extract_user_from_token(token)
        
        assert user_info["email"] == ""
    
    def test_extract_user_from_token_invalid_token(self):
        """Test extraction with invalid token"""
        with pytest.raises(ValidationError):
            extract_user_from_token("invalid.token")
    
    def test_extract_user_from_token_with_bearer_prefix(self):
        """Test extraction with Bearer prefix"""
        data = {"user_id": 7, "username": "test_user7"}
        token = create_access_token(data)
        bearer_token = f"Bearer {token}"
        
        user_info = extract_user_from_token(bearer_token)
        
        assert user_info["user_id"] == 7

