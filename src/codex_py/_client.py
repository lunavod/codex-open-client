"""Optional OpenAI SDK wrapper using Codex OAuth tokens."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codex_py._config import CODEX_BASE_URL, DEFAULT_TOKEN_PATH


def Client(
    *,
    headless: bool = False,
    no_browser: bool = False,
    token_path: Path = DEFAULT_TOKEN_PATH,
    **kwargs: Any,
) -> Any:
    """Create an OpenAI client authenticated with Codex OAuth.

    The client is configured to use the ChatGPT backend API
    (chatgpt.com/backend-api/codex) with the correct headers.

    Requires the 'openai' extra: pip install "codex-py[openai]"

    All extra keyword arguments are forwarded to openai.OpenAI().
    """
    try:
        import openai
    except ImportError:
        raise ImportError(
            "The 'openai' package is required for Client(). "
            "Install it with: pip install \"codex-py[openai]\""
        ) from None

    from codex_py._api import build_headers
    from codex_py._auth import get_token

    token = get_token(headless=headless, no_browser=no_browser, token_path=token_path)
    headers = build_headers(token)

    # The OpenAI SDK adds its own Authorization header, so we remove ours
    # and pass the token as api_key. We inject the extra headers via default_headers.
    extra_headers = {k: v for k, v in headers.items() if k != "Authorization"}

    kwargs.setdefault("api_key", token)
    kwargs.setdefault("base_url", CODEX_BASE_URL)
    kwargs.setdefault("default_headers", extra_headers)
    return openai.OpenAI(**kwargs)
