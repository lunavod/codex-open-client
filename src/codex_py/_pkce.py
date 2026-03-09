"""PKCE (Proof Key for Code Exchange) utilities."""

import base64
import hashlib
import secrets


def generate_verifier(length: int = 128) -> str:
    """Generate a random code verifier (43-128 characters, URL-safe)."""
    return secrets.token_urlsafe(length)[:length]


def generate_challenge(verifier: str) -> str:
    """Generate a code challenge from a verifier (SHA-256, base64url-encoded)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
