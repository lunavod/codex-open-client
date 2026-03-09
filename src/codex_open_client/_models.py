"""Models resource for the Codex API client."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from codex_open_client._config import CODEX_BASE_URL, CODEX_CLIENT_VERSION
from codex_open_client._errors import APIConnectionError, APITimeoutError, raise_for_status
from codex_open_client._types import Model

if TYPE_CHECKING:
    from codex_open_client._client import CodexClient

_CACHE_TTL = 300  # 5 minutes


@dataclass
class _ModelsCache:
    models: list[Model] = field(default_factory=list)
    fetched_at: float = 0.0

    def is_stale(self) -> bool:
        return time.time() - self.fetched_at > _CACHE_TTL


class Models:
    """Access the Codex models endpoint.

    Usage::

        models = client.models.list()
        for m in models:
            print(m.slug, m.context_window)
    """

    def __init__(self, client: CodexClient) -> None:
        self._client = client
        self._cache = _ModelsCache()

    def list(self, *, force_refresh: bool = False) -> list[Model]:
        """List models available to the authenticated user.

        Results are cached for 5 minutes. Pass ``force_refresh=True`` to bypass.
        """
        if not force_refresh and not self._cache.is_stale():
            return self._cache.models

        headers = self._client._build_headers()

        try:
            resp = httpx.get(
                f"{CODEX_BASE_URL}/models",
                params={"client_version": CODEX_CLIENT_VERSION},
                headers=headers,
                timeout=self._client._timeout,
            )
        except httpx.TimeoutException as e:
            raise APITimeoutError(str(e), cause=e) from e
        except httpx.ConnectError as e:
            raise APIConnectionError(str(e), cause=e) from e

        if resp.status_code >= 400:
            body: Any = None
            try:
                body = resp.json()
            except (ValueError, json.JSONDecodeError):
                body = resp.text
            raise_for_status(resp.status_code, body)

        data: dict[str, Any] = resp.json()
        raw_models: list[dict[str, Any]] = data.get("models", [])

        models = [_parse_model(m) for m in raw_models]
        self._cache = _ModelsCache(models=models, fetched_at=time.time())
        return models


def _parse_model(data: dict[str, Any]) -> Model:
    reasoning_levels: list[str] = []
    for level in data.get("supported_reasoning_levels", []):
        if isinstance(level, dict):
            reasoning_levels.append(level.get("effort", ""))
        else:
            reasoning_levels.append(str(level))

    return Model(
        slug=data.get("slug", ""),
        display_name=data.get("display_name", data.get("slug", "")),
        context_window=data.get("context_window"),
        reasoning_levels=reasoning_levels,
        input_modalities=data.get("input_modalities", []),
        supports_parallel_tool_calls=data.get("supports_parallel_tool_calls", False),
        priority=data.get("priority", 0),
    )
