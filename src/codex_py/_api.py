"""Codex API helpers — models listing, request headers, JWT parsing."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from codex_py._auth import get_token
from codex_py._config import (
    CODEX_BASE_URL,
    CODEX_CLIENT_VERSION,
    DEFAULT_TOKEN_PATH,
)


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without signature verification (we trust the issuer)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload = parts[1]
    # Add padding
    payload += "=" * (-len(payload) % 4)
    result: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload))
    return result


def get_account_id(token: str) -> str | None:
    """Extract the ChatGPT account ID from a Codex OAuth JWT."""
    try:
        payload = _decode_jwt_payload(token)
        auth_info: dict[str, Any] = payload.get("https://api.openai.com/auth", {})
        account_id: str | None = (
            auth_info.get("chatgpt_account_id") or auth_info.get("account_id")
        )
        return account_id
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def build_headers(token: str) -> dict[str, str]:
    """Build the headers required for Codex API requests."""
    headers = {
        "Authorization": f"Bearer {token}",
        "OpenAI-Beta": "responses=experimental",
        "originator": "codex_cli_rs",
    }
    account_id = get_account_id(token)
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id
    return headers


def list_models(
    *,
    headless: bool = False,
    no_browser: bool = False,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> list[dict[str, Any]]:
    """List models available to the authenticated user.

    Returns a list of model dicts from the Codex backend, each containing
    keys like: slug, display_name, context_window, supported_reasoning_levels, etc.
    """
    token = get_token(headless=headless, no_browser=no_browser, token_path=token_path)
    resp = httpx.get(
        f"{CODEX_BASE_URL}/models",
        params={"client_version": CODEX_CLIENT_VERSION},
        headers=build_headers(token),
    )
    resp.raise_for_status()
    models: list[dict[str, Any]] = resp.json()["models"]
    return models
