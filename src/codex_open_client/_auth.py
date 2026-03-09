"""Core OAuth authentication flow."""

from __future__ import annotations

import secrets
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from codex_open_client._config import (
    AUDIENCE,
    AUTH_ENDPOINT,
    CLIENT_ID,
    DEFAULT_TOKEN_PATH,
    REDIRECT_URI,
    SCOPES,
    TOKEN_ENDPOINT,
    TokenData,
    load_tokens,
    save_tokens,
)
from codex_open_client._pkce import generate_challenge, generate_verifier


@dataclass
class PendingLogin:
    """Opaque state for a two-step login flow.

    Returned by ``start_login()``, passed to ``finish_login()``.
    """

    url: str
    _verifier: str
    _state: str


def _build_auth_url(challenge: str, state: str) -> str:
    """Build the full authorization URL."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "audience": AUDIENCE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def _extract_code_from_url(url: str) -> str:
    """Extract the authorization code from a callback URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    if "error" in params:
        desc = params.get("error_description", params["error"])[0]
        raise RuntimeError(f"OAuth error: {desc}")

    codes = params.get("code")
    if not codes:
        raise ValueError(
            "No authorization code found in URL. "
            "Make sure you copied the full redirect URL."
        )
    return codes[0]


def _exchange_code(code: str, verifier: str) -> TokenData:
    """Exchange an authorization code for tokens."""
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code >= 400:
        try:
            body = resp.json()
            detail = body.get("error_description", body.get("error", resp.text))
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Token exchange failed ({resp.status_code}): {detail}")
    data = resp.json()

    expires_at = None
    if "expires_in" in data:
        expires_at = time.time() + data["expires_in"]

    known = {"access_token", "refresh_token", "expires_in", "token_type", "id_token", "scope"}
    extra = {k: v for k, v in data.items() if k not in known}

    return TokenData(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=expires_at,
        token_type=data.get("token_type", "Bearer"),
        id_token=data.get("id_token"),
        scope=data.get("scope"),
        _extra=extra,
    )


def refresh(
    refresh_token: str,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> TokenData:
    """Use a refresh token to obtain a new access token."""
    resp = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code >= 400:
        try:
            body = resp.json()
            detail = body.get("error_description", body.get("error", resp.text))
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Token refresh failed ({resp.status_code}): {detail}")
    data = resp.json()

    expires_at = None
    if "expires_in" in data:
        expires_at = time.time() + data["expires_in"]

    known = {"access_token", "refresh_token", "expires_in", "token_type", "id_token", "scope"}
    extra = {k: v for k, v in data.items() if k not in known}

    tokens = TokenData(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", refresh_token),
        expires_at=expires_at,
        token_type=data.get("token_type", "Bearer"),
        id_token=data.get("id_token"),
        scope=data.get("scope"),
        _extra=extra,
    )
    save_tokens(tokens, token_path)
    return tokens


def login(
    *,
    headless: bool = False,
    no_browser: bool = False,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> TokenData:
    """Run the full OAuth PKCE login flow.

    Args:
        headless: If True, print the auth URL and prompt the user to paste
            the callback URL back. No local server is started.
        no_browser: If True, print the auth URL instead of opening a browser,
            but still start the local callback server to catch the redirect.
        token_path: Where to store the resulting tokens.

    Returns:
        The obtained token data.
    """
    verifier = generate_verifier()
    challenge = generate_challenge(verifier)
    state = secrets.token_urlsafe(32)
    auth_url = _build_auth_url(challenge, state)

    if headless:
        # Headless mode: no server, user pastes the redirect URL
        print("Open this URL in your browser to authenticate:\n")
        print(f"  {auth_url}\n")
        print("After authenticating, you'll be redirected to a URL that may not load.")
        print("Copy the full URL from your browser's address bar and paste it here.\n")
        callback_url = input("Paste redirect URL: ").strip()
        code = _extract_code_from_url(callback_url)
    else:
        # Interactive mode: start local server
        from codex_open_client._server import wait_for_callback

        if no_browser:
            print("Open this URL in your browser to authenticate:\n")
            print(f"  {auth_url}\n")
        else:
            print("Opening browser for authentication...")
            webbrowser.open(auth_url)

        code = wait_for_callback()

    tokens = _exchange_code(code, verifier)
    save_tokens(tokens, token_path)
    return tokens


def get_token(
    *,
    headless: bool = False,
    no_browser: bool = False,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> str:
    """Get a valid access token, handling cache, refresh, and login automatically.

    Args:
        headless: If True and login is needed, use headless mode.
        no_browser: If True and login is needed, print URL instead of opening browser.
        token_path: Path to the token storage file.

    Returns:
        A valid access token string.
    """
    tokens = load_tokens(token_path)

    if tokens is not None:
        # Token exists and isn't expired — use it
        if not tokens.is_expired():
            return tokens.access_token

        # Try to refresh
        if tokens.refresh_token:
            try:
                tokens = refresh(tokens.refresh_token, token_path)
                return tokens.access_token
            except httpx.HTTPStatusError:
                pass  # Refresh failed, fall through to login

    # No valid token — need to log in
    tokens = login(headless=headless, no_browser=no_browser, token_path=token_path)
    return tokens.access_token


def start_login() -> PendingLogin:
    """Begin a two-step login flow.

    Returns a ``PendingLogin`` with a ``.url`` attribute containing the
    OAuth URL to present to the user. Pass the result to ``finish_login()``
    along with the callback URL after the user authenticates.

    Example::

        auth = codex_open_client.start_login()
        # ... show auth.url to the user, let them authenticate ...
        tokens = codex_open_client.finish_login(auth, callback_url="http://localhost:1455/...")
    """
    verifier = generate_verifier()
    challenge = generate_challenge(verifier)
    state = secrets.token_urlsafe(32)
    auth_url = _build_auth_url(challenge, state)

    return PendingLogin(url=auth_url, _verifier=verifier, _state=state)


def finish_login(
    pending: PendingLogin,
    *,
    callback_url: str,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> TokenData:
    """Complete a two-step login flow.

    Args:
        pending: The ``PendingLogin`` returned by ``start_login()``.
        callback_url: The full redirect URL (including the ``code`` parameter)
            after the user authenticated in their browser.
        token_path: Where to store the resulting tokens.

    Returns:
        The obtained token data.
    """
    code = _extract_code_from_url(callback_url)
    tokens = _exchange_code(code, pending._verifier)
    save_tokens(tokens, token_path)
    return tokens


