"""Tests for _models.py — model parsing and cache."""

from codex_open_client._models import _ModelsCache, _parse_model


def test_parse_model_full() -> None:
    data = {
        "slug": "gpt-5.3-codex",
        "display_name": "gpt-5.3-codex",
        "context_window": 272000,
        "supported_reasoning_levels": [
            {"effort": "low"},
            {"effort": "medium"},
            {"effort": "high"},
        ],
        "input_modalities": ["text", "image"],
        "supports_parallel_tool_calls": True,
        "priority": 0,
    }
    model = _parse_model(data)
    assert model.slug == "gpt-5.3-codex"
    assert model.context_window == 272000
    assert model.reasoning_levels == ["low", "medium", "high"]
    assert model.input_modalities == ["text", "image"]
    assert model.supports_parallel_tool_calls is True


def test_parse_model_minimal() -> None:
    data = {"slug": "test-model"}
    model = _parse_model(data)
    assert model.slug == "test-model"
    assert model.display_name == "test-model"
    assert model.context_window is None
    assert model.reasoning_levels == []


def test_cache_starts_stale() -> None:
    cache = _ModelsCache()
    assert cache.is_stale()


def test_cache_fresh() -> None:
    import time

    cache = _ModelsCache(fetched_at=time.time())
    assert not cache.is_stale()
