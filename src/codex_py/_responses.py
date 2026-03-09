"""Responses resource for the Codex API client."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal, overload

import httpx

from codex_py._config import CODEX_BASE_URL
from codex_py._errors import APIConnectionError, APITimeoutError, raise_for_status
from codex_py._stream import ResponseStream
from codex_py._types import (
    FunctionCallOutput,
    FunctionTool,
    InputMessage,
    Reasoning,
    Response,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseReasoningItem,
    TextConfig,
)

if TYPE_CHECKING:
    from codex_py._client import CodexClient

# Input item types that can be serialized
_InputItem = (
    InputMessage
    | ResponseOutputMessage
    | FunctionCallOutput
    | ResponseFunctionToolCall
    | ResponseReasoningItem
)


class Responses:
    """Access the Codex responses endpoint.

    Usage::

        response = client.responses.create(
            model="gpt-5.1-codex-mini",
            instructions="You are helpful.",
            input="Hello!",
        )
        print(response.output_text)
    """

    def __init__(self, client: CodexClient) -> None:
        self._client = client

    @overload
    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str | list[_InputItem | dict[str, Any]],
        stream: Literal[False] = False,
        tools: list[FunctionTool | dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning: Reasoning | None = None,
        text: TextConfig | None = None,
        service_tier: Literal["auto", "flex", "priority"] | None = None,
        include: list[str] | None = None,
        previous_response_id: str | None = None,
        timeout: float | None = None,
    ) -> Response: ...

    @overload
    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str | list[_InputItem | dict[str, Any]],
        stream: Literal[True],
        tools: list[FunctionTool | dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning: Reasoning | None = None,
        text: TextConfig | None = None,
        service_tier: Literal["auto", "flex", "priority"] | None = None,
        include: list[str] | None = None,
        previous_response_id: str | None = None,
        timeout: float | None = None,
    ) -> ResponseStream: ...

    @overload
    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str | list[_InputItem | dict[str, Any]],
        stream: bool,
        tools: list[FunctionTool | dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning: Reasoning | None = None,
        text: TextConfig | None = None,
        service_tier: Literal["auto", "flex", "priority"] | None = None,
        include: list[str] | None = None,
        previous_response_id: str | None = None,
        timeout: float | None = None,
    ) -> Response | ResponseStream: ...

    def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str | list[_InputItem | dict[str, Any]],
        stream: bool = False,
        tools: list[FunctionTool | dict[str, Any]] | None = None,
        tool_choice: Literal["auto", "none", "required"] | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning: Reasoning | None = None,
        text: TextConfig | None = None,
        service_tier: Literal["auto", "flex", "priority"] | None = None,
        include: list[str] | None = None,
        previous_response_id: str | None = None,
        timeout: float | None = None,
    ) -> Response | ResponseStream:
        """Create a response from the Codex API.

        Always streams internally from the API (``stream: true`` in the body).
        When ``stream=False`` (default), collects the stream and returns the
        final ``Response``. When ``stream=True``, returns a ``ResponseStream``
        that yields events as they arrive.
        """
        # Build the input list
        input_list = _serialize_input(input)

        body: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": input_list,
            "store": False,
            "stream": True,  # Always stream from API
        }

        if tools:
            body["tools"] = [_serialize_tool(t) for t in tools]
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        if parallel_tool_calls is not None:
            body["parallel_tool_calls"] = parallel_tool_calls
        if reasoning is not None:
            body["reasoning"] = _serialize_dataclass(reasoning)
        if text is not None:
            body["text"] = _serialize_dataclass(text)
        if service_tier is not None:
            body["service_tier"] = service_tier
        if include is not None:
            body["include"] = include
        if previous_response_id is not None:
            body["previous_response_id"] = previous_response_id

        headers = self._client._build_headers()
        req_timeout = timeout if timeout is not None else self._client._timeout

        resp = self._request_with_retry(headers, body, req_timeout)

        response_stream = ResponseStream(resp)

        if stream:
            return response_stream

        return response_stream.get_final_response()

    def _request_with_retry(
        self,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> httpx.Response:
        """Send the request with retry logic for 429/5xx."""
        import time

        from codex_py._errors import _parse_retry_after

        max_retries = self._client._max_retries

        for attempt in range(max_retries + 1):
            try:
                resp = httpx.post(
                    f"{CODEX_BASE_URL}/responses",
                    headers=headers,
                    json=body,
                    timeout=timeout,
                )
            except httpx.TimeoutException as e:
                raise APITimeoutError(str(e), cause=e) from e
            except httpx.ConnectError as e:
                raise APIConnectionError(str(e), cause=e) from e

            if resp.status_code < 400:
                return resp

            resp_body: Any = None
            try:
                resp_body = resp.json()
            except (ValueError, json.JSONDecodeError):
                resp_body = resp.text

            # Retry on 429/5xx if we have attempts left
            is_retryable = resp.status_code in (429, 500, 502, 503, 504)
            if is_retryable and attempt < max_retries:
                if resp.status_code == 429:
                    # Try to parse retry-after from the error message
                    msg = resp_body if isinstance(resp_body, str) else str(resp_body)
                    retry_after = _parse_retry_after(msg)
                    wait = retry_after if retry_after else (2 ** attempt)
                else:
                    wait = float(2 ** attempt)
                time.sleep(wait)
                continue

            raise_for_status(resp.status_code, resp_body)

        raise AssertionError("unreachable")  # pragma: no cover


def _serialize_input(
    input: str | list[Any],
) -> list[dict[str, Any]]:
    """Convert input to the API's expected list format."""
    if isinstance(input, str):
        return [{"role": "user", "content": input}]

    result: list[dict[str, Any]] = []
    for item in input:
        if isinstance(item, dict):
            result.append(item)
        else:
            result.append(_serialize_dataclass(item))
    return result


def _serialize_tool(tool: FunctionTool | dict[str, Any]) -> dict[str, Any]:
    if isinstance(tool, dict):
        return tool
    return _serialize_dataclass(tool)


def _serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Serialize a dataclass, handling nested content parts."""
    if isinstance(obj, dict):
        return obj

    d = asdict(obj)
    # Remove None values
    return {k: v for k, v in d.items() if v is not None}
