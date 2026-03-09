"""OAuth constants and token storage."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# OAuth parameters (from Codex CLI)
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_ENDPOINT = "https://auth.openai.com/oauth/authorize"
TOKEN_ENDPOINT = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPES = "openid profile email offline_access"
AUDIENCE = "https://api.openai.com/v1"

# Codex API (ChatGPT backend, not api.openai.com)
CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_CLIENT_VERSION = "0.99.0"

# Default token file (interop with Codex CLI)
DEFAULT_TOKEN_PATH = Path.home() / ".codex" / "auth.json"


@dataclass
class TokenData:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    token_type: str = "Bearer"
    id_token: str | None = None
    scope: str | None = None
    _extra: dict[str, object] = field(default_factory=dict)

    def is_expired(self, margin_seconds: int = 60) -> bool:
        """Check if the token is expired (with a safety margin)."""
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - margin_seconds)

    def to_dict(self) -> dict[str, object]:
        d = {k: v for k, v in asdict(self).items() if v is not None and k != "_extra"}
        d.update(self._extra)
        return d


def load_tokens(path: Path = DEFAULT_TOKEN_PATH) -> TokenData | None:
    """Load tokens from disk. Returns None if file doesn't exist or is invalid."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if "access_token" not in data:
        return None

    known = {"access_token", "refresh_token", "expires_at", "token_type", "id_token", "scope"}
    extra = {k: v for k, v in data.items() if k not in known}
    return TokenData(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=data.get("expires_at"),
        token_type=data.get("token_type", "Bearer"),
        id_token=data.get("id_token"),
        scope=data.get("scope"),
        _extra=extra,
    )


def save_tokens(tokens: TokenData, path: Path = DEFAULT_TOKEN_PATH) -> None:
    """Save tokens to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens.to_dict(), indent=2) + "\n", encoding="utf-8")
