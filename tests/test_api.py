import base64
import json
from typing import Any

from codex_open_client._api import _decode_jwt_payload, build_headers, get_account_id


def _make_jwt(payload: dict[str, Any]) -> str:
    """Create a fake JWT with the given payload (no signature verification needed)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return f"{header.decode()}.{body.decode()}.fakesig"


def test_decode_jwt_payload() -> None:
    payload: dict[str, Any] = {"sub": "user123", "name": "Test"}
    token = _make_jwt(payload)
    decoded = _decode_jwt_payload(token)
    assert decoded["sub"] == "user123"
    assert decoded["name"] == "Test"


def test_get_account_id() -> None:
    payload: dict[str, Any] = {
        "https://api.openai.com/auth": {
            "chatgpt_account_id": "acct_abc123",
        }
    }
    token = _make_jwt(payload)
    assert get_account_id(token) == "acct_abc123"


def test_get_account_id_fallback() -> None:
    payload: dict[str, Any] = {
        "https://api.openai.com/auth": {
            "account_id": "acct_fallback",
        }
    }
    token = _make_jwt(payload)
    assert get_account_id(token) == "acct_fallback"


def test_get_account_id_missing() -> None:
    payload: dict[str, Any] = {"sub": "user"}
    token = _make_jwt(payload)
    assert get_account_id(token) is None


def test_get_account_id_invalid_jwt() -> None:
    assert get_account_id("not.a.valid.jwt.at.all") is None


def test_build_headers_with_account_id() -> None:
    payload: dict[str, Any] = {
        "https://api.openai.com/auth": {
            "chatgpt_account_id": "acct_test",
        }
    }
    token = _make_jwt(payload)
    headers = build_headers(token)

    assert headers["Authorization"] == f"Bearer {token}"
    assert headers["ChatGPT-Account-ID"] == "acct_test"
    assert headers["OpenAI-Beta"] == "responses=experimental"
    assert headers["originator"] == "codex_cli_rs"


def test_build_headers_without_account_id() -> None:
    payload: dict[str, Any] = {"sub": "user"}
    token = _make_jwt(payload)
    headers = build_headers(token)

    assert "Authorization" in headers
    assert "ChatGPT-Account-ID" not in headers
