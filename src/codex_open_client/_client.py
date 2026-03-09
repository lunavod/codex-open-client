"""CodexClient — the main entry point for the Codex API."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import httpx

from codex_open_client._api import build_headers, get_account_id
from codex_open_client._auth import get_token
from codex_open_client._config import DEFAULT_TOKEN_PATH, load_tokens
from codex_open_client._models import Models
from codex_open_client._responses import Responses


class CodexClient:
    """Python client for the Codex API.

    Handles authentication, token refresh, and provides typed access
    to the Codex responses and models endpoints.

    Usage::

        import codex_open_client

        client = codex_open_client.CodexClient()
        response = client.responses.create(
            model="gpt-5.1-codex-mini",
            instructions="You are helpful.",
            input="Hello!",
        )
        print(response.output_text)
    """

    def __init__(
        self,
        *,
        headless: bool = False,
        no_browser: bool = False,
        token_path: str | Path = DEFAULT_TOKEN_PATH,
        login_handler: Callable[[str], str] | None = None,
        max_retries: int = 2,
        timeout: float = 120.0,
    ) -> None:
        self._headless = headless
        self._no_browser = no_browser
        self._token_path = Path(token_path)
        self._login_handler = login_handler
        self._max_retries = max_retries
        self._timeout = timeout

        # Eagerly authenticate
        self._token = self._authenticate()
        self._account_id = get_account_id(self._token)

        # Sub-resources
        self.responses = Responses(self)
        self.models = Models(self)

    def _authenticate(self) -> str:
        """Get a valid access token."""
        if self._login_handler is not None:
            # Check cache first
            tokens = load_tokens(self._token_path)
            if tokens is not None and not tokens.is_expired():
                return tokens.access_token
            if tokens is not None and tokens.refresh_token:
                from codex_open_client._auth import refresh

                try:
                    tokens = refresh(tokens.refresh_token, self._token_path)
                    return tokens.access_token
                except (httpx.HTTPStatusError, RuntimeError, OSError):
                    pass  # Refresh failed, fall through to login handler
            # Use the custom login handler
            from codex_open_client._auth import finish_login, start_login

            auth = start_login()
            callback_url = self._login_handler(auth.url)
            tokens = finish_login(auth, callback_url=callback_url, token_path=self._token_path)
            return tokens.access_token

        return get_token(
            headless=self._headless,
            no_browser=self._no_browser,
            token_path=self._token_path,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with the current token."""
        return build_headers(self._token)

    def login(self) -> None:
        """Re-authenticate, replacing the current token."""
        from codex_open_client._auth import login as auth_login

        tokens = auth_login(
            headless=self._headless,
            no_browser=self._no_browser,
            token_path=self._token_path,
        )
        self._token = tokens.access_token
        self._account_id = get_account_id(self._token)

    @property
    def token(self) -> str:
        """The current access token."""
        return self._token

    @property
    def account_id(self) -> str | None:
        """The ChatGPT account ID extracted from the current token."""
        return self._account_id
