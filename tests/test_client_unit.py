"""Unit tests for CodexClient (no network)."""

import time
from pathlib import Path

from codex_open_client._config import TokenData, save_tokens


def test_client_from_cached_token(tmp_path: Path) -> None:
    """CodexClient should use cached tokens without hitting the network."""
    path = tmp_path / "auth.json"
    save_tokens(
        TokenData(access_token="test_token_123", expires_at=time.time() + 3600),
        path,
    )

    from codex_open_client._client import CodexClient

    client = CodexClient(token_path=path)
    assert client.token == "test_token_123"
    assert client.responses is not None
    assert client.models is not None


def test_client_login_handler(tmp_path: Path) -> None:
    """CodexClient should call the login_handler when no cached token exists."""
    path = tmp_path / "auth.json"
    handler_called = False

    def fake_handler(url: str) -> str:
        nonlocal handler_called
        handler_called = True
        assert "authorize" in url
        # Return a fake callback URL — this will fail at code exchange,
        # so we can't test the full flow without a real auth server.
        # We just verify the handler is called.
        raise RuntimeError("test: handler was called")

    from codex_open_client._client import CodexClient

    try:
        CodexClient(token_path=path, login_handler=fake_handler)
    except RuntimeError as e:
        assert "handler was called" in str(e)

    assert handler_called


def test_client_login_handler_with_cache(tmp_path: Path) -> None:
    """login_handler should not be called when a cached token is available."""
    path = tmp_path / "auth.json"
    save_tokens(
        TokenData(access_token="cached", expires_at=time.time() + 3600),
        path,
    )

    handler_called = False

    def handler(url: str) -> str:
        nonlocal handler_called
        handler_called = True
        return ""

    from codex_open_client._client import CodexClient

    client = CodexClient(token_path=path, login_handler=handler)
    assert client.token == "cached"
    assert not handler_called
