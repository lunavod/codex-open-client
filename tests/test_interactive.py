"""Interactive login tests that require a human at the keyboard.

These tests exercise the real OAuth flow — a browser opens, the user
authenticates, and the token is verified.

Never run by default. Run with:
    pytest -m interactive -s -k test_login_auto

The ``-s`` flag is required so that print() and input() work.
Run one at a time with ``-k`` since each requires a separate auth session.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import codex_open_client

pytestmark = pytest.mark.interactive


@pytest.fixture(autouse=True)
def _require_no_capture(request: pytest.FixtureRequest) -> None:
    """Fail early if stdout capture is active (i.e. -s was not passed)."""
    manager: Any = request.config.pluginmanager.getplugin("capturemanager")
    if manager and manager.is_globally_capturing():
        pytest.fail(
            "Interactive tests require -s (--capture=no). "
            "Run with: pytest -m interactive -s"
        )


def test_login_auto(tmp_path: Path) -> None:
    """login() default mode: opens browser + local callback server.

    1. A browser tab opens with the OAuth login page.
    2. Authenticate in the browser.
    3. The browser redirects to localhost:1455 — the server catches it.
    """
    print("\n=== AUTO LOGIN TEST ===")
    print("A browser window will open. Please authenticate.\n")

    tokens = codex_open_client.login(token_path=tmp_path / "auth.json")

    assert tokens.access_token
    assert isinstance(tokens.access_token, str)
    assert len(tokens.access_token) > 0
    print(f"\n  Got access token ({len(tokens.access_token)} chars)")

    headers = codex_open_client.build_headers(tokens.access_token)
    assert "Authorization" in headers
    assert "ChatGPT-Account-ID" in headers
    print(f"  Account ID: {headers['ChatGPT-Account-ID']}")


def test_login_no_browser(tmp_path: Path) -> None:
    """login(no_browser=True): prints URL, local server catches callback.

    1. A URL is printed in the terminal.
    2. Open it in your browser and authenticate.
    3. The browser redirects to localhost:1455 — the server catches it.
    """
    print("\n=== NO-BROWSER LOGIN TEST ===")
    print("A URL will be printed below. Open it in your browser.\n")

    tokens = codex_open_client.login(
        no_browser=True,
        token_path=tmp_path / "auth.json",
    )

    assert tokens.access_token
    assert len(tokens.access_token) > 0
    print(f"\n  Got access token ({len(tokens.access_token)} chars)")


def test_login_headless(tmp_path: Path) -> None:
    """login(headless=True): prints URL, user pastes callback URL.

    1. A URL is printed in the terminal.
    2. Open it in your browser and authenticate.
    3. You'll be redirected to a page that won't load (localhost:1455).
    4. Copy the full URL from the address bar and paste it here.
    """
    print("\n=== HEADLESS LOGIN TEST ===")
    print("A URL will be printed. After authenticating, paste the redirect URL.\n")

    tokens = codex_open_client.login(
        headless=True,
        token_path=tmp_path / "auth.json",
    )

    assert tokens.access_token
    assert len(tokens.access_token) > 0
    print(f"\n  Got access token ({len(tokens.access_token)} chars)")


def test_start_finish_login(tmp_path: Path) -> None:
    """Manual two-step flow: start_login() + finish_login().

    1. A URL is printed in the terminal.
    2. Open it in your browser and authenticate.
    3. You'll be redirected to a page that won't load (localhost:1455).
    4. Copy the full URL from the address bar and paste it here.
    """
    print("\n=== TWO-STEP LOGIN TEST ===")

    auth = codex_open_client.start_login()
    assert auth.url
    assert "authorize" in auth.url

    print("Open this URL in your browser to authenticate:\n")
    print(f"  {auth.url}\n")
    print("After authenticating, copy the full redirect URL from your browser.")
    print("(It will be a localhost URL that doesn't load.)\n")

    callback_url = input("Paste redirect URL: ").strip()

    tokens = codex_open_client.finish_login(
        auth,
        callback_url=callback_url,
        token_path=tmp_path / "auth.json",
    )

    assert tokens.access_token
    assert len(tokens.access_token) > 0
    print(f"\n  Got access token ({len(tokens.access_token)} chars)")

    from codex_open_client._api import build_headers

    headers = build_headers(tokens.access_token)
    assert "ChatGPT-Account-ID" in headers
    print(f"  Account ID: {headers['ChatGPT-Account-ID']}")


def test_login_handler(tmp_path: Path) -> None:
    """CodexClient with a custom login_handler.

    1. A URL is printed in the terminal.
    2. Open it in your browser and authenticate.
    3. You'll be redirected to a page that won't load (localhost:1455).
    4. Copy the full URL from the address bar and paste it here.
    """
    print("\n=== LOGIN HANDLER TEST ===")
    print("Testing CodexClient with a custom login handler.\n")

    def my_handler(url: str) -> str:
        print("Open this URL in your browser to authenticate:\n")
        print(f"  {url}\n")
        print("After authenticating, copy the full redirect URL.\n")
        return input("Paste redirect URL: ").strip()

    client = codex_open_client.CodexClient(
        login_handler=my_handler,
        token_path=tmp_path / "auth.json",
    )

    assert client.token
    assert client.account_id
    print(f"\n  Client created with token ({len(client.token)} chars)")
    print(f"  Account ID: {client.account_id}")

    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input="Say hello",
    )
    assert response.output_text
    print(f"  API response: {response.output_text[:80]}")
