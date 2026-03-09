"""Codex API helpers — request headers and JWT parsing."""

from __future__ import annotations

import base64
import json
from typing import Any


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
