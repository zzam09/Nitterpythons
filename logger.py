#!/usr/bin/env python3
"""
Structured JSON logging for production-grade debugging and monitoring.
Provides request tracing, context-aware logging, and easy integration with log aggregation tools.
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

# Thread-local storage for request context
_context = threading.local()


class StructuredLogger:
    """JSON-structured logger with request tracing and context."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        
    def _log(self, level: str, message: str, **kwargs) -> None:
        """Internal method to format and emit structured log entry."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "logger": self.name,
            "message": message,
            "request_id": getattr(_context, 'request_id', None),
            "user_id": getattr(_context, 'user_id', None),
            "context": getattr(_context, 'context', 'system'),
            **kwargs
        }
        
        # Remove None values for cleaner logs
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        
        # Emit as JSON
        log_line = json.dumps(log_entry, default=str)
        self.logger.log(getattr(logging, level.upper()), log_line)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self._log("info", message, **kwargs)
    
    def warn(self, message: str, **kwargs) -> None:
        """Log warning level message."""
        self._log("warn", message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error level message."""
        self._log("error", message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message."""
        self._log("debug", message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical level message."""
        self._log("critical", message, **kwargs)


class RequestContext:
    """Context manager for request-scoped logging."""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None, context: str = "request"):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.context = context
        self.previous_context = None
    
    def __enter__(self):
        # Store current context
        self.previous_context = {
            'request_id': getattr(_context, 'request_id', None),
            'user_id': getattr(_context, 'user_id', None),
            'context': getattr(_context, 'context', 'system'),
        }
        
        # Set new context
        _context.request_id = self.request_id
        _context.user_id = self.user_id
        _context.context = self.context
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        if self.previous_context:
            _context.request_id = self.previous_context['request_id']
            _context.user_id = self.previous_context['user_id']
            _context.context = self.previous_context['context']


class FunctionContext:
    """Context manager for function-level logging."""
    
    def __init__(self, logger: StructuredLogger, function_name: str, **kwargs):
        self.logger = logger
        self.function_name = function_name
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"Starting {self.function_name}",
            function=self.function_name,
            **self.kwargs
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else None
        
        if exc_type:
            self.logger.error(
                f"Failed {self.function_name}",
                function=self.function_name,
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None,
                duration_ms=round(duration * 1000, 2) if duration else None,
                **self.kwargs
            )
        else:
            self.logger.info(
                f"Completed {self.function_name}",
                function=self.function_name,
                duration_ms=round(duration * 1000, 2) if duration else None,
                **self.kwargs
            )


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for structured output."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(message)s',  # We handle formatting in StructuredLogger
        handlers=[logging.StreamHandler()]
    )


# Convenience decorators
def log_function(logger_name: str = None):
    """Decorator to automatically log function entry/exit."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            function_name = f"{func.__module__}.{func.__name__}"
            
            with FunctionContext(logger, function_name, args_count=len(args), kwargs_keys=list(kwargs.keys())):
                return func(*args, **kwargs)
        
        # Set a unique name for the wrapper function to avoid Flask endpoint conflicts
        wrapper.__name__ = f"{func.__name__}_wrapped_{id(func)}"
        return wrapper
    return decorator


def log_api_call(logger_name: str = None):
    """Decorator specifically for API endpoints."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or 'api')
            function_name = f"api.{func.__name__}"
            
            # Try to extract user info from Flask request if available
            user_id = None
            try:
                from flask import request
                if hasattr(request, 'args') and 'user_id' in request.args:
                    user_id = request.args.get('user_id')
            except ImportError:
                pass
            
            with RequestContext(user_id=user_id, context='api'):
                with FunctionContext(logger, function_name, user_id=user_id):
                    return func(*args, **kwargs)
        
        # Set a unique name for the wrapper function to avoid Flask endpoint conflicts
        wrapper.__name__ = f"{func.__name__}_api_wrapped_{id(func)}"
        return wrapper
    return decorator


# Module-level logger instance
system_logger = get_logger('system')
