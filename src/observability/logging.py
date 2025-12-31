"""
Structured logging for observability
Logs in JSON format for easy parsing by Grafana/Loki
"""
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
import uuid

# Context variable for request ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID if available (from context or extra)
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the 'extra' parameter
        # These are added as attributes to the LogRecord
        # Exclude standard LogRecord attributes
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
            'pathname', 'process', 'processName', 'relativeCreated', 'thread',
            'threadName', 'exc_info', 'exc_text', 'stack_info', 'getMessage'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                log_data[key] = value
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup structured logging
    
    Args:
        level: Logging level (INFO, DEBUG, WARNING, ERROR)
        log_file: Optional path to log file. If provided, logs will also be written to file.
                  If None, logs only go to stdout.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        import os
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def set_request_id(request_id: str):
    """Set request ID in context"""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_var.get()


def generate_request_id() -> str:
    """Generate a new request ID"""
    return str(uuid.uuid4())


class RequestLogger:
    """Logger with request context"""
    
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
        set_request_id(request_id)
    
    def _log_with_extra(self, level: int, message: str, **extra_fields):
        """Log with structured fields using extra parameter"""
        # Build extra dict with request_id and additional fields
        extra = {"request_id": self.request_id}
        extra.update(extra_fields)
        
        # Use the logger's log method with extra parameter
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, **extra_fields):
        self._log_with_extra(logging.INFO, message, **extra_fields)
    
    def error(self, message: str, **extra_fields):
        self._log_with_extra(logging.ERROR, message, **extra_fields)
    
    def warning(self, message: str, **extra_fields):
        self._log_with_extra(logging.WARNING, message, **extra_fields)
    
    def debug(self, message: str, **extra_fields):
        self._log_with_extra(logging.DEBUG, message, **extra_fields)

