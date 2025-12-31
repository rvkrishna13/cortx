"""
Unit tests for custom exception classes
"""
import pytest
from src.utils.exceptions import (
    FinancialMCPServerError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    ValidationError,
    NotFoundError,
    MCPToolError,
    InvalidInputError
)


class TestFinancialMCPServerError:
    """Tests for base exception class"""
    
    def test_base_exception_creation(self):
        """Test creating base exception"""
        error = FinancialMCPServerError("Test error", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_CODE"
    
    def test_base_exception_without_code(self):
        """Test creating base exception without error code"""
        error = FinancialMCPServerError("Test error")
        assert error.message == "Test error"
        assert error.error_code is None


class TestDatabaseError:
    """Tests for database error classes"""
    
    def test_database_error_creation(self):
        """Test creating database error"""
        original = Exception("Original error")
        error = DatabaseError("Database error", original)
        assert error.message == "Database error"
        assert error.original_error == original
        assert error.error_code == "DB_ERROR"
    
    def test_database_connection_error(self):
        """Test creating database connection error"""
        original = Exception("Connection failed")
        error = DatabaseConnectionError("Failed to connect", original)
        assert error.message == "Failed to connect"
        assert error.original_error == original
        assert error.error_code == "DB_CONNECTION_ERROR"
    
    def test_database_connection_error_default(self):
        """Test database connection error with default message"""
        error = DatabaseConnectionError()
        assert "Failed to connect to database" in error.message
        assert error.error_code == "DB_CONNECTION_ERROR"
    
    def test_database_query_error(self):
        """Test creating database query error"""
        original = Exception("Query failed")
        error = DatabaseQueryError("Query error", original)
        assert error.message == "Query error"
        assert error.original_error == original
        assert error.error_code == "DB_QUERY_ERROR"


class TestValidationError:
    """Tests for validation error classes"""
    
    def test_validation_error_creation(self):
        """Test creating validation error"""
        error = ValidationError("Invalid input", "field_name")
        assert error.message == "Invalid input"
        assert error.field == "field_name"
        assert error.error_code == "VALIDATION_ERROR"
    
    def test_validation_error_without_field(self):
        """Test creating validation error without field"""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.field is None
    
    def test_invalid_input_error(self):
        """Test creating invalid input error"""
        error = InvalidInputError("field_name", "bad_value", "Must be positive")
        assert "field_name" in error.message
        assert "bad_value" in error.message
        assert "Must be positive" in error.message
        assert error.field == "field_name"
        assert error.error_code == "INVALID_INPUT"


class TestNotFoundError:
    """Tests for not found error"""
    
    def test_not_found_error_with_id(self):
        """Test creating not found error with ID"""
        error = NotFoundError("Portfolio", "123")
        assert "Portfolio" in error.message
        assert "123" in error.message
        assert error.error_code == "NOT_FOUND"
    
    def test_not_found_error_without_id(self):
        """Test creating not found error without ID"""
        error = NotFoundError("Portfolio")
        assert "Portfolio" in error.message
        assert error.error_code == "NOT_FOUND"


class TestMCPToolError:
    """Tests for MCP tool error"""
    
    def test_mcp_tool_error_creation(self):
        """Test creating MCP tool error"""
        original = Exception("Tool execution failed")
        error = MCPToolError("tool_name", "Tool error message", original)
        assert "tool_name" in error.message
        assert "Tool error message" in error.message
        assert error.tool_name == "tool_name"
        assert error.original_error == original
        assert error.error_code == "MCP_TOOL_ERROR"
    
    def test_mcp_tool_error_without_original(self):
        """Test creating MCP tool error without original error"""
        error = MCPToolError("tool_name", "Tool error message")
        assert error.tool_name == "tool_name"
        assert error.original_error is None

