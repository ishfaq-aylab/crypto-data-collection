#!/usr/bin/env python3
"""Error handling service with retry logic and recovery mechanisms."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from loguru import logger

from interfaces import IErrorHandler


class ErrorHandler(IErrorHandler):
    """Error handling service with retry logic."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.error_counts: Dict[str, int] = {}
        self.last_error_times: Dict[str, datetime] = {}
        self.recovery_handlers: Dict[str, List[Callable]] = {}
    
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle an error and return True if recovered."""
        try:
            error_type = type(error).__name__
            error_key = f"{context.get('collector', 'unknown')}_{error_type}"
            
            # Record error
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            self.last_error_times[error_key] = datetime.now()
            
            logger.error(f"❌ Error in {context.get('collector', 'unknown')}: {error}")
            
            # Check if we should retry
            if not self.should_retry(error, self.error_counts[error_key]):
                logger.error(f"❌ Max retries exceeded for {error_key}")
                return False
            
            # Get retry delay
            delay = self.get_retry_delay(error, self.error_counts[error_key])
            logger.info(f"⏳ Retrying in {delay:.2f} seconds...")
            
            # Wait before retry
            await asyncio.sleep(delay)
            
            # Try recovery handlers
            if error_key in self.recovery_handlers:
                for handler in self.recovery_handlers[error_key]:
                    try:
                        if await handler(error, context):
                            logger.info(f"✅ Recovered from {error_type} using handler")
                            return True
                    except Exception as e:
                        logger.error(f"❌ Error in recovery handler: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")
            return False
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if operation should be retried."""
        # Don't retry if max attempts exceeded
        if attempt > self.max_retries:
            return False
        
        # Don't retry certain types of errors
        non_retryable_errors = [
            "ValueError",
            "TypeError", 
            "AttributeError",
            "KeyError",
            "ImportError",
            "ModuleNotFoundError"
        ]
        
        if type(error).__name__ in non_retryable_errors:
            return False
        
        # Don't retry if too many consecutive errors
        if attempt > 5:
            return False
        
        return True
    
    def get_retry_delay(self, error: Exception, attempt: int) -> float:
        """Get retry delay in seconds."""
        # Exponential backoff with jitter
        delay = min(
            self.base_delay * (self.backoff_factor ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.1, 0.5) * delay
        delay += jitter
        
        return delay
    
    def add_recovery_handler(self, error_type: str, collector: str, handler: Callable) -> None:
        """Add a recovery handler for specific error type and collector."""
        key = f"{collector}_{error_type}"
        if key not in self.recovery_handlers:
            self.recovery_handlers[key] = []
        self.recovery_handlers[key].append(handler)
        logger.info(f"📝 Added recovery handler for {key}")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        now = datetime.now()
        recent_errors = 0
        
        for error_key, last_time in self.last_error_times.items():
            if (now - last_time).total_seconds() < 300:  # Last 5 minutes
                recent_errors += self.error_counts.get(error_key, 0)
        
        return {
            "total_error_types": len(self.error_counts),
            "recent_errors": recent_errors,
            "error_counts": dict(self.error_counts),
            "last_error_times": {
                k: v.isoformat() for k, v in self.last_error_times.items()
            }
        }
    
    def reset_error_counts(self) -> None:
        """Reset error counts."""
        self.error_counts.clear()
        self.last_error_times.clear()
        logger.info("🔄 Reset error counts")


class ConnectionErrorHandler(ErrorHandler):
    """Specialized error handler for connection errors."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection_errors = [
            "ConnectionError",
            "ConnectionRefusedError", 
            "ConnectionResetError",
            "TimeoutError",
            "asyncio.TimeoutError"
        ]
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if connection error should be retried."""
        error_name = type(error).__name__
        
        # Always retry connection errors
        if error_name in self.connection_errors:
            return attempt <= self.max_retries * 2  # More retries for connection errors
        
        return super().should_retry(error, attempt)
    
    def get_retry_delay(self, error: Exception, attempt: int) -> float:
        """Get retry delay for connection errors."""
        error_name = type(error).__name__
        
        if error_name in self.connection_errors:
            # Longer delays for connection errors
            delay = min(
                self.base_delay * 2 * (self.backoff_factor ** (attempt - 1)),
                self.max_delay * 2
            )
            return delay + random.uniform(0.5, 2.0)
        
        return super().get_retry_delay(error, attempt)


# Global error handler instance
error_handler = ConnectionErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return error_handler
