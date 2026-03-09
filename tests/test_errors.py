"""Tests for _errors.py exception hierarchy."""

import pytest

from codex_py._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthError,
    CodexError,
    ContextWindowError,
    InvalidRequestError,
    RateLimitError,
    ServerError,
    StreamError,
    _parse_retry_after,
    raise_for_status,
)


def test_hierarchy() -> None:
    assert issubclass(APIError, CodexError)
    assert issubclass(AuthError, APIError)
    assert issubclass(RateLimitError, APIError)
    assert issubclass(InvalidRequestError, APIError)
    assert issubclass(ContextWindowError, InvalidRequestError)
    assert issubclass(ServerError, APIError)


def test_raise_for_status_401() -> None:
    with pytest.raises(AuthError) as exc_info:
        raise_for_status(401, {"detail": "Unauthorized"})
    assert exc_info.value.status_code == 401
    assert exc_info.value.message == "Unauthorized"


def test_raise_for_status_429() -> None:
    with pytest.raises(RateLimitError):
        raise_for_status(429, {"detail": "Rate limited"})


def test_raise_for_status_400() -> None:
    with pytest.raises(InvalidRequestError):
        raise_for_status(400, {"detail": "Bad request"})


def test_raise_for_status_500() -> None:
    with pytest.raises(ServerError):
        raise_for_status(500, {"detail": "Internal error"})


def test_raise_for_status_context_length() -> None:
    body = {"error": {"code": "context_length_exceeded", "message": "Too long"}}
    with pytest.raises(ContextWindowError):
        raise_for_status(400, body)


def test_raise_for_status_error_dict() -> None:
    with pytest.raises(APIError) as exc_info:
        raise_for_status(422, {"error": {"message": "Unprocessable", "code": "invalid"}})
    assert exc_info.value.message == "Unprocessable"
    assert exc_info.value.code == "invalid"


def test_raise_for_status_string_body() -> None:
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(502, "Bad Gateway")
    assert exc_info.value.message == "Bad Gateway"


def test_parse_retry_after() -> None:
    assert _parse_retry_after("try again in 2.500s") == 2.5
    assert _parse_retry_after("Try Again In 10s") == 10.0
    assert _parse_retry_after("no info here") is None


def test_rate_limit_auto_parse_retry() -> None:
    e = RateLimitError("Please try again in 3.000s", status_code=429)
    assert e.retry_after == 3.0


def test_rate_limit_explicit_retry() -> None:
    e = RateLimitError("msg", status_code=429, retry_after=5.0)
    assert e.retry_after == 5.0


def test_raise_for_status_403() -> None:
    with pytest.raises(AuthError) as exc_info:
        raise_for_status(403, {"detail": "Forbidden"})
    assert exc_info.value.status_code == 403


def test_api_connection_error() -> None:
    e = APIConnectionError("Connection refused", cause=OSError("refused"))
    assert isinstance(e, CodexError)
    assert e.message == "Connection refused"
    assert isinstance(e.cause, OSError)


def test_api_timeout_error() -> None:
    e = APITimeoutError("Timed out", cause=TimeoutError())
    assert isinstance(e, APIConnectionError)
    assert isinstance(e, CodexError)


def test_stream_error() -> None:
    e = StreamError("Stream closed")
    assert isinstance(e, CodexError)


def test_raise_for_status_error_string() -> None:
    """Error body with a plain string 'error' field."""
    with pytest.raises(APIError) as exc_info:
        raise_for_status(422, {"error": "Something went wrong"})
    assert exc_info.value.message == "Something went wrong"


def test_raise_for_status_non_dict_body() -> None:
    """Non-dict, non-string body should be str()-ified."""
    with pytest.raises(ServerError) as exc_info:
        raise_for_status(500, 12345)
    assert "12345" in exc_info.value.message
