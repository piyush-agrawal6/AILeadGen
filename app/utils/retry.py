import logging
from typing import Any, Callable, TypeVar
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

logger = logging.getLogger("leadengine.retry")

T = TypeVar("T")


def is_transient_http_error(exc: BaseException) -> bool:
    """Return True if exception is transient network or server error (e.g. 429, 502, 503, 504, timeout)."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.ReadError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # Retry 429 Too Many Requests and 5xx Server Errors
        code = exc.response.status_code
        if code == 429 or code in (500, 502, 503, 504):
            return True
        # Do not retry 400, 401, 403, 404, 410, etc.
        return False
    return False


def make_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a tenacity retry decorator for network calls."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, min=min_wait, max=max_wait),
        retry=retry_if_exception(is_transient_http_error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
