"""Live tests that use real OAuth tokens and hit the Codex API.

Never run by default. Run explicitly with:
    pytest -m live
"""

import pytest

from codex_py._api import build_headers, get_account_id
from codex_py._auth import get_token
from codex_py._config import CODEX_BASE_URL, DEFAULT_TOKEN_PATH, load_tokens

pytestmark = pytest.mark.live


@pytest.fixture()
def token() -> str:
    """Get a real token, skipping if no cached credentials exist."""
    tokens = load_tokens(DEFAULT_TOKEN_PATH)
    if tokens is None:
        pytest.skip("No cached tokens in ~/.codex/auth.json")
    tok = get_token(token_path=DEFAULT_TOKEN_PATH)
    assert tok
    return tok


def test_get_token_returns_string(token: str) -> None:
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_has_account_id(token: str) -> None:
    account_id = get_account_id(token)
    assert account_id is not None, "JWT should contain a ChatGPT account ID"
    assert isinstance(account_id, str)


def test_build_headers(token: str) -> None:
    headers = build_headers(token)
    assert "Authorization" in headers
    assert "ChatGPT-Account-ID" in headers
    assert headers["OpenAI-Beta"] == "responses=experimental"
    assert headers["originator"] == "codex_cli_rs"


def test_token_refresh() -> None:
    """Verify that loading + refreshing tokens works end-to-end."""
    tokens = load_tokens(DEFAULT_TOKEN_PATH)
    if tokens is None:
        pytest.skip("No cached tokens in ~/.codex/auth.json")
    if tokens.refresh_token is None:
        pytest.skip("No refresh token available")

    from codex_py._auth import refresh

    new_tokens = refresh(tokens.refresh_token, DEFAULT_TOKEN_PATH)
    assert new_tokens.access_token
    assert isinstance(new_tokens.access_token, str)


def test_responses_endpoint(token: str) -> None:
    """Make a real call to the Codex responses endpoint."""
    import httpx

    headers = build_headers(token)
    resp = httpx.post(
        f"{CODEX_BASE_URL}/responses",
        headers=headers,
        json={
            "model": "gpt-5.1-codex-mini",
            "input": [{"role": "user", "content": "Reply with exactly: pong"}],
            "instructions": "You are a helpful assistant.",
            "store": False,
            "stream": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    # Streaming response — check that we get SSE events
    assert "event: response.created" in resp.text
