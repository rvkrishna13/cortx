"""
Custom exception classes for the application
"""
from typing import Optional


class FinancialMCPServerError(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseError(FinancialMCPServerError):
    """Database-related errors"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message, error_code="DB_ERROR")


class DatabaseConnectionError(DatabaseError):
    """Database connection errors"""
    def __init__(self, message: str = "Failed to connect to database", original_error: Optional[Exception] = None):
        super().__init__(message, original_error)
        self.error_code = "DB_CONNECTION_ERROR"


class DatabaseQueryError(DatabaseError):
    """Database query execution errors"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, original_error)
        self.error_code = "DB_QUERY_ERROR"


class ValidationError(FinancialMCPServerError):
    """Input validation errors"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message, error_code="VALIDATION_ERROR")


class NotFoundError(FinancialMCPServerError):
    """Resource not found errors"""
    def __init__(self, resource_type: str, resource_id: Optional[str] = None):
        if resource_id:
            message = f"{resource_type} with ID {resource_id} not found"
        else:
            message = f"{resource_type} not found"
        super().__init__(message, error_code="NOT_FOUND")


class MCPToolError(FinancialMCPServerError):
    """MCP tool execution errors"""
    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        self.tool_name = tool_name
        self.original_error = original_error
        super().__init__(f"Tool '{tool_name}': {message}", error_code="MCP_TOOL_ERROR")


class InvalidInputError(ValidationError):
    """Invalid input parameter errors"""
    def __init__(self, field: str, value: any, reason: str):
        message = f"Invalid value for '{field}': {value}. {reason}"
        super().__init__(message, field)
        self.error_code = "INVALID_INPUT"

