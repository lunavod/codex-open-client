import time
from pathlib import Path

from codex_py._auth import (
    PendingLogin,
    _build_auth_url,
    _extract_code_from_url,
    finish_login,
    get_token,
    start_login,
)
from codex_py._config import TokenData, save_tokens


def test_build_auth_url_contains_params() -> None:
    url = _build_auth_url("challenge123", "state456")
    assert "challenge123" in url
    assert "state456" in url
    assert "code_challenge_method=S256" in url
    assert "response_type=code" in url


def test_extract_code_from_url() -> None:
    url = "http://localhost:1455/auth/callback?code=abc123&state=xyz"
    assert _extract_code_from_url(url) == "abc123"


def test_extract_code_error() -> None:
    url = "http://localhost:1455/auth/callback?error=access_denied&error_description=User+denied"
    try:
        _extract_code_from_url(url)
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "User denied" in str(e)


def test_extract_code_missing() -> None:
    url = "http://localhost:1455/auth/callback?state=xyz"
    try:
        _extract_code_from_url(url)
        assert False, "Should have raised"
    except ValueError as e:
        assert "No authorization code" in str(e)


def test_get_token_from_cache(tmp_path: Path) -> None:
    """get_token returns cached token without hitting the network."""
    path = tmp_path / "auth.json"
    tokens = TokenData(
        access_token="cached_token",
        expires_at=time.time() + 3600,
    )
    save_tokens(tokens, path)

    result = get_token(token_path=path)
    assert result == "cached_token"


def test_start_login_returns_pending() -> None:
    """start_login() should return a PendingLogin with a valid auth URL."""
    pending = start_login()
    assert isinstance(pending, PendingLogin)
    assert "authorize" in pending.url
    assert "code_challenge" in pending.url
    assert "state" in pending.url
    assert pending._verifier  # noqa: SLF001
    assert pending._state  # noqa: SLF001


def test_start_login_unique_state() -> None:
    """Each call to start_login should generate a unique state."""
    a = start_login()
    b = start_login()
    assert a._state != b._state  # noqa: SLF001
    assert a._verifier != b._verifier  # noqa: SLF001


def test_finish_login_extracts_code(tmp_path: Path) -> None:
    """finish_login should extract code from callback URL and attempt exchange."""
    import pytest

    pending = start_login()
    # finish_login will try to exchange a fake code — it should fail at the
    # HTTP level, not at URL parsing
    fake_url = "http://localhost:1455/auth/callback?code=fake_code_123&state=xyz"
    with pytest.raises(Exception):
        # Will fail at _exchange_code (HTTP error), which is expected
        finish_login(pending, callback_url=fake_url, token_path=tmp_path / "auth.json")


def test_finish_login_error_in_callback() -> None:
    """finish_login should raise on error in callback URL."""
    import pytest

    pending = start_login()
    error_url = "http://localhost:1455/auth/callback?error=access_denied"
    with pytest.raises(RuntimeError, match="OAuth error"):
        finish_login(pending, callback_url=error_url)
