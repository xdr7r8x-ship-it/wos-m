"""
Rate Limiter for WOS-M Integrations
Provides rate limiting, timeout, retry, and exponential backoff for external API calls.
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import logging
import time
from typing import Optional, Callable, Any, TypeVar, Awaitable
from functools import wraps
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiting."""
    max_requests: int = 10  # Max requests per window
    window_seconds: float = 1.0  # Time window in seconds
    timeout_seconds: float = 30.0  # Request timeout
    max_retries: int = 3  # Max retry attempts
    base_backoff: float = 1.0  # Base backoff seconds
    max_backoff: float = 30.0  # Max backoff seconds
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)  # Status codes to retry


class RateLimiter:
    """
    Token bucket rate limiter with async support.
    Provides timeout and retry with exponential backoff.
    """
    
    def __init__(self, config: Optional[RateLimiterConfig] = None):
        self.config = config or RateLimiterConfig()
        self._tokens = self.config.max_requests
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            
            # Refill tokens based on elapsed time
            tokens_to_add = elapsed * (self.config.max_requests / self.config.window_seconds)
            self._tokens = min(self.config.max_requests, self._tokens + tokens_to_add)
            self._last_update = now
            
            if self._tokens < 1:
                wait_time = (1 - self._tokens) * (self.config.window_seconds / self.config.max_requests)
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for token")
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1
    
    async def execute_with_timeout(
        self,
        coro: Awaitable[T],
        timeout: Optional[float] = None
    ) -> T:
        """Execute a coroutine with timeout."""
        timeout_val = timeout or self.config.timeout_seconds
        try:
            return await asyncio.wait_for(coro, timeout=timeout_val)
        except asyncio.TimeoutError:
            raise RateLimitTimeout(f"Request timed out after {timeout_val}s")
    
    def calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        import random
        # Calculate base backoff without jitter
        backoff = self.config.base_backoff * (2 ** attempt)
        # Apply jitter (0.5 to 1.5) but cap at max_backoff
        jitter_multiplier = 0.5 + random.random()  # 0.5 to 1.5
        backoff_with_jitter = backoff * jitter_multiplier
        # Cap at max_backoff to avoid excessive waits
        return min(backoff_with_jitter, self.config.max_backoff)
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[T]]
    ) -> T:
        """Execute a function with retry and exponential backoff."""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                await self.acquire()
                return await self.execute_with_timeout(func())
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Request timed out (attempt {attempt + 1}/{self.config.max_retries})")
            except RateLimitError as e:
                last_exception = e
                if e.retry_after:
                    backoff = e.retry_after
                else:
                    backoff = self.calculate_backoff(attempt)
                logger.warning(f"Rate limited, waiting {backoff:.2f}s (attempt {attempt + 1}/{self.config.max_retries})")
                await asyncio.sleep(backoff)
            except Exception as e:
                # Check if it's a retryable status code
                if hasattr(e, 'status_code') and e.status_code in self.config.retry_on_status:
                    last_exception = e
                    backoff = self.calculate_backoff(attempt)
                    logger.warning(f"Retryable error {e.status_code}, waiting {backoff:.2f}s")
                    await asyncio.sleep(backoff)
                else:
                    # Non-retryable error
                    raise
        
        # All retries exhausted
        raise RateLimitExhausted(f"All {self.config.max_retries} retries exhausted: {last_exception}")


class RateLimitError(Exception):
    """Base exception for rate limiting errors."""
    def __init__(self, message: str, retry_after: Optional[float] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.status_code = status_code


class RateLimitTimeout(RateLimitError):
    """Exception for timeout errors."""
    pass


class RateLimitExhausted(RateLimitError):
    """Exception when all retries are exhausted."""
    pass


def mask_sensitive_data(url: str, headers: Optional[dict] = None) -> str:
    """
    Mask sensitive data in URLs and headers for safe logging.
    Does NOT print API keys, tokens, or authorization headers.
    """
    # Mask common API key patterns
    patterns = [
        (r'(api[_-]?key=)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(token=)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(key=)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(secret=)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(password=)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(Bearer\s+)[^&\s"\']+', r'\1***REDACTED***'),
        (r'(Basic\s+)[^&\s"\']+', r'\1***REDACTED***'),
    ]
    
    masked_url = url
    for pattern, replacement in patterns:
        masked_url = re.sub(pattern, replacement, masked_url, flags=re.IGNORECASE)
    
    return masked_url


def safe_log_request(method: str, url: str, **kwargs) -> None:
    """Log request without exposing sensitive data."""
    safe_url = mask_sensitive_data(url)
    logger.info(f"API Request: {method} {safe_url}")
    if kwargs.get('headers'):
        # Log headers but redact sensitive ones
        safe_headers = {}
        for k, v in kwargs['headers'].items():
            if any(s in k.lower() for s in ['auth', 'token', 'key', 'secret', 'password', 'bearer', 'basic']):
                safe_headers[k] = '***REDACTED***'
            else:
                safe_headers[k] = v
        logger.debug(f"Headers: {safe_headers}")


def safe_log_response(status: int, url: str, **kwargs) -> None:
    """Log response without exposing sensitive data."""
    safe_url = mask_sensitive_data(url)
    logger.info(f"API Response: {status} {safe_url}")


def safe_log_error(error: Exception, url: str) -> None:
    """Log error without exposing sensitive data."""
    safe_url = mask_sensitive_data(url)
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Check if error message contains sensitive patterns
    sensitive_patterns = ['api_key', 'token', 'secret', 'password', 'bearer', 'basic', 'auth']
    for pattern in sensitive_patterns:
        if pattern in error_msg.lower():
            error_msg = f"[Error contains sensitive data - {error_type}]"
            break
    
    logger.error(f"API Error: {error_type} - {error_msg} (URL: {safe_url})")


# Default global rate limiter instance
_default_limiter: Optional[RateLimiter] = None


def get_default_limiter() -> RateLimiter:
    """Get or create the default rate limiter."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter()
    return _default_limiter


def set_default_limiter(limiter: RateLimiter) -> None:
    """Set the default rate limiter."""
    global _default_limiter
    _default_limiter = limiter
