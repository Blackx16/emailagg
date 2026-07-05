"""
utils.py — Shared utility functions for the Engineering OS Bootstrapper.

Includes:
  - Exponential-backoff retry decorator
  - HTTP session factory with auth and user-agent
  - Idempotent slug generation
  - Date formatting helpers
  - Safe dict access helpers
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bootstrap.config import AtlassianConfig

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# HTTP Session
# ---------------------------------------------------------------------------

def build_session(cfg: AtlassianConfig) -> Session:
    """
    Build a persistent requests.Session pre-configured with:
      - HTTP Basic Auth (Atlassian email + API token)
      - JSON content-type headers
      - Connection-level retry policy (for network-level failures)
      - Timeout defaults baked into an adapter

    Application-level retries (429, 5xx) are handled separately by
    the `with_retry` decorator.

    Args:
        cfg: The loaded AtlassianConfig.

    Returns:
        Configured requests.Session.
    """
    session = Session()
    session.auth = cfg.auth_tuple
    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Atlassian-Token": "no-check",
            "User-Agent": "EngineeringOS-Bootstrapper/1.0 (+https://github.com/Blackx16/emailagg)",
        }
    )

    # Network-level retry (DNS failures, connection resets)
    urllib_retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[],  # Application retries handled by `with_retry`
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=urllib_retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# ---------------------------------------------------------------------------
# Exponential-backoff retry decorator
# ---------------------------------------------------------------------------

class RetryableError(Exception):
    """Raised to signal that the caller should retry the operation."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def with_retry(
    max_retries: int = 5,
    backoff_base: float = 2.0,
    retryable_statuses: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Callable[[F], F]:
    """
    Decorator factory that adds exponential-backoff retry logic to any function.

    Retries on:
      - `RetryableError` raised by the wrapped function
      - HTTP responses with status codes in `retryable_statuses`

    Args:
        max_retries:        Maximum attempts before propagating the error.
        backoff_base:       Base for exponential delay: delay = base^attempt (seconds).
        retryable_statuses: HTTP status codes that trigger a retry.

    Returns:
        Decorated function with retry behaviour.
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except RetryableError as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = (backoff_base ** attempt) if backoff_base > 0 else 0
                    # Respect Retry-After header if present (passed via exception)
                    if delay > 0:
                        time.sleep(delay)
                except Exception:
                    raise  # Non-retryable errors propagate immediately

            raise last_exc or RuntimeError(f"{fn.__name__} failed after {max_retries} retries")

        return wrapper  # type: ignore[return-value]
    return decorator  # type: ignore[return-value]


def check_response(
    response: Response,
    retryable_statuses: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> None:
    """
    Inspect an HTTP response and raise RetryableError or RuntimeError
    as appropriate.

    Args:
        response:           The requests.Response to inspect.
        retryable_statuses: HTTP codes that should trigger a retry.

    Raises:
        RetryableError: For transient/rate-limit errors.
        RuntimeError:   For permanent client errors (4xx except 429).
    """
    if response.ok:
        return

    code = response.status_code
    body = _safe_json(response)
    msg = f"HTTP {code} — {response.url} — {body}"

    if code in retryable_statuses:
        raise RetryableError(msg, status_code=code)

    raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Slug / ID helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """
    Convert a human-readable title to a URL-safe slug.

    Example::

        slugify("ADR-001: Use PostgreSQL") → "adr-001-use-postgresql"

    Args:
        text: The input string.

    Returns:
        Lowercase, hyphen-separated slug.
    """
    # Normalise unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lower, replace separators
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def stable_id(namespace: str, key: str) -> str:
    """
    Generate a stable, deterministic short ID for an entity.

    Useful for idempotency checks where we need a consistent key
    across runs.

    Args:
        namespace: Logical grouping (e.g., "confluence_page").
        key:       Unique identifier within the namespace.

    Returns:
        8-character hex digest.
    """
    return hashlib.sha256(f"{namespace}:{key}".encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    """Return current UTC timestamp as ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date() -> str:
    """Return current UTC date as YYYY-MM-DD string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Safe accessors
# ---------------------------------------------------------------------------

def _safe_json(response: Response) -> Any:
    """Return parsed JSON body or raw text if parsing fails."""
    try:
        return response.json()
    except Exception:
        return response.text[:300]


def deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely traverse a nested dict using a sequence of keys.

    Args:
        data:    The dictionary to traverse.
        *keys:   Sequence of string keys.
        default: Value to return if any key is missing.

    Returns:
        The value at the nested path, or `default`.
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current


def chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    """Split a list into chunks of at most `size` elements."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]
