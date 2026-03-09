import time
from pathlib import Path

from codex_py._auth import _build_auth_url, _extract_code_from_url, get_token
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
