import base64
import hashlib

from codex_py._pkce import generate_challenge, generate_verifier


def test_verifier_length() -> None:
    v = generate_verifier(43)
    assert len(v) == 43

    v = generate_verifier(128)
    assert len(v) == 128


def test_verifier_url_safe() -> None:
    v = generate_verifier()
    # URL-safe base64 chars only
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in allowed for c in v)


def test_verifier_is_random() -> None:
    v1 = generate_verifier()
    v2 = generate_verifier()
    assert v1 != v2


def test_challenge_matches_sha256() -> None:
    verifier = "test_verifier_string"
    challenge = generate_challenge(verifier)

    # Manually compute expected challenge
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert challenge == expected
