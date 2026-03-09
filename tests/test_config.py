import json
import time
from pathlib import Path

from codex_py._config import TokenData, load_tokens, save_tokens


def test_token_not_expired() -> None:
    t = TokenData(access_token="abc", expires_at=time.time() + 3600)
    assert not t.is_expired()


def test_token_expired() -> None:
    t = TokenData(access_token="abc", expires_at=time.time() - 10)
    assert t.is_expired()


def test_token_no_expiry_not_expired() -> None:
    t = TokenData(access_token="abc")
    assert not t.is_expired()


def test_token_expired_within_margin() -> None:
    t = TokenData(access_token="abc", expires_at=time.time() + 30)
    assert t.is_expired(margin_seconds=60)


def test_save_and_load(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    tokens = TokenData(
        access_token="access123",
        refresh_token="refresh456",
        expires_at=1700000000.0,
    )
    save_tokens(tokens, path)

    loaded = load_tokens(path)
    assert loaded is not None
    assert loaded.access_token == "access123"
    assert loaded.refresh_token == "refresh456"
    assert loaded.expires_at == 1700000000.0


def test_load_missing_file(tmp_path: Path) -> None:
    assert load_tokens(tmp_path / "nonexistent.json") is None


def test_load_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    path.write_text("not json", encoding="utf-8")
    assert load_tokens(path) is None


def test_load_no_access_token(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    path.write_text(json.dumps({"refresh_token": "x"}), encoding="utf-8")
    assert load_tokens(path) is None


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "dir" / "auth.json"
    tokens = TokenData(access_token="abc")
    save_tokens(tokens, path)
    assert path.is_file()


def test_roundtrip_preserves_extra_fields(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    # Simulate a file with extra fields from Codex CLI
    data = {"access_token": "abc", "custom_field": "value123"}
    path.write_text(json.dumps(data), encoding="utf-8")

    loaded = load_tokens(path)
    assert loaded is not None
    assert loaded._extra["custom_field"] == "value123"

    save_tokens(loaded, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["custom_field"] == "value123"
