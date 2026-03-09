"""Exception hierarchy for the Codex API client."""

from __future__ import annotations

import re


class CodexError(Exception):
    """Base exception for all codex-open-client errors."""


class APIError(CodexError):
    """An error response from the Codex API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str | None = None,
        body: object = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.body = body
        super().__init__(message)


class AuthError(APIError):
    """401 — token expired, refresh failed, or unauthorized."""


class InvalidRequestError(APIError):
    """400 — bad parameters, missing fields, etc."""


class RateLimitError(APIError):
    """429 — rate limited. Check ``retry_after`` for when to retry."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        code: str | None = None,
        body: object = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, code=code, body=body)
        if retry_after is None:
            retry_after = _parse_retry_after(message)
        self.retry_after = retry_after


class ContextWindowError(InvalidRequestError):
    """Input too long for the model's context window."""


class QuotaExceededError(APIError):
    """Subscription quota exhausted."""


class ServerError(APIError):
    """5xx — server-side or overloaded."""


class APIConnectionError(CodexError):
    """Network failure — no response received."""

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        self.message = message
        self.cause = cause
        super().__init__(message)


class APITimeoutError(APIConnectionError):
    """Request timed out."""


class StreamError(CodexError):
    """Stream closed unexpectedly or response incomplete."""


_RETRY_PATTERN = re.compile(r"try again in (\d+(?:\.\d+)?)s", re.IGNORECASE)


def _parse_retry_after(message: str) -> float | None:
    """Extract retry-after seconds from error messages like 'try again in 2.500s'."""
    m = _RETRY_PATTERN.search(message)
    if m:
        return float(m.group(1))
    return None


def raise_for_status(status_code: int, body: object) -> None:
    """Raise the appropriate CodexError subclass for an HTTP error response."""
    message = ""
    code: str | None = None

    if isinstance(body, dict):
        # API errors come in various shapes
        detail = body.get("detail")
        error = body.get("error")
        if isinstance(detail, str):
            message = detail
        elif isinstance(error, dict):
            message = error.get("message", str(body))
            code = error.get("code")
        elif isinstance(error, str):
            message = error
        else:
            message = str(body)
    elif isinstance(body, str):
        message = body
    else:
        message = str(body)

    if code == "context_length_exceeded":
        raise ContextWindowError(message, status_code=status_code, code=code, body=body)

    if status_code == 401:
        raise AuthError(message, status_code=status_code, code=code, body=body)
    elif status_code == 429:
        raise RateLimitError(message, status_code=status_code, code=code, body=body)
    elif status_code == 400:
        raise InvalidRequestError(message, status_code=status_code, code=code, body=body)
    elif status_code == 403:
        raise AuthError(message, status_code=status_code, code=code, body=body)
    elif status_code >= 500:
        raise ServerError(message, status_code=status_code, code=code, body=body)
    else:
        raise APIError(message, status_code=status_code, code=code, body=body)
