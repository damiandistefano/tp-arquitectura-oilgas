"""Retry logic with exponential backoff for ingestion operations."""

import time
from functools import wraps
from typing import Callable, TypeVar

from .config import get_retry_backoff_seconds, get_retry_count
from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int | None = None, backoff_seconds: int | None = None
) -> Callable:
    """Decorator to retry a function with exponential backoff.

    Uses DATA_PIPELINE_RETRIES and DATA_PIPELINE_RETRY_BACKOFF_SECONDS from config if not provided.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            retries = max_retries if max_retries is not None else get_retry_count()
            base_backoff = (
                backoff_seconds if backoff_seconds is not None else get_retry_backoff_seconds()
            )

            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = base_backoff * (2 ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {retries} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator
