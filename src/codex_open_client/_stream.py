"""SSE parser and ResponseStream for the Codex API."""

from __future__ import annotations

import json
from typing import Any, Iterator, Protocol

from codex_open_client._errors import StreamError
from codex_open_client._types import (
    OutputText,
    ReasoningSummary,
    Response,
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseFailedEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseFunctionToolCall,
    ResponseIncompleteEvent,
    ResponseInProgressEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputMessage,
    ResponseOutputTextDeltaEvent,
    ResponseOutputTextDoneEvent,
    ResponseReasoningItem,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
    ResponseStreamEvent,
    Usage,
)


class _HasText(Protocol):
    """Minimal interface for an HTTP response with a .text property."""

    @property
    def text(self) -> str: ...  # pragma: no cover


def _parse_response(data: dict[str, Any]) -> Response:
    """Parse a Response object from raw JSON dict."""
    output = _parse_output_items(data.get("output", []))

    usage = None
    if data.get("usage"):
        u = data["usage"]
        usage = Usage(
            input_tokens=u.get("input_tokens", 0),
            output_tokens=u.get("output_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
        )

    return Response(
        id=data.get("id", ""),
        model=data.get("model", ""),
        output=output,
        status=data.get("status"),
        usage=usage,
        error=None,
    )


def _parse_output_items(items: list[dict[str, Any]]) -> list[Any]:
    """Parse a list of output item dicts into typed objects."""
    result: list[Any] = []
    for item in items:
        result.append(_parse_output_item(item))
    return result


def _parse_output_item(item: dict[str, Any]) -> Any:
    """Parse a single output item dict into a typed object."""
    item_type = item.get("type", "")

    if item_type == "message":
        content_list: list[Any] = []
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                content_list.append(OutputText(text=c.get("text", "")))
            # Skip unknown content types rather than silently coercing
        return ResponseOutputMessage(
            id=item.get("id", ""),
            content=content_list,
            role=item.get("role", "assistant"),
            status=item.get("status"),
        )
    elif item_type == "function_call":
        return ResponseFunctionToolCall(
            call_id=item.get("call_id", ""),
            name=item.get("name", ""),
            arguments=item.get("arguments", ""),
            id=item.get("id"),
            status=item.get("status"),
        )
    elif item_type == "reasoning":
        summaries = [
            ReasoningSummary(text=s.get("text", ""))
            for s in item.get("summary", [])
        ]
        return ResponseReasoningItem(
            id=item.get("id", ""),
            summary=summaries,
            encrypted_content=item.get("encrypted_content"),
        )
    else:
        # Unknown type — return raw dict so callers can inspect it
        return item


def _parse_sse_event(event_type: str, data: dict[str, Any]) -> ResponseStreamEvent | None:
    """Convert a raw SSE event into a typed ResponseStreamEvent."""

    if event_type == "response.created":
        return ResponseCreatedEvent(response=_parse_response(data.get("response", data)))
    elif event_type == "response.in_progress":
        return ResponseInProgressEvent(response=_parse_response(data.get("response", data)))
    elif event_type == "response.completed":
        return ResponseCompletedEvent(response=_parse_response(data.get("response", data)))
    elif event_type == "response.failed":
        return ResponseFailedEvent(response=_parse_response(data.get("response", data)))
    elif event_type == "response.incomplete":
        return ResponseIncompleteEvent(response=_parse_response(data.get("response", data)))
    elif event_type == "response.output_item.added":
        return ResponseOutputItemAddedEvent(
            item=_parse_output_item(data.get("item", {})),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.output_item.done":
        return ResponseOutputItemDoneEvent(
            item=_parse_output_item(data.get("item", {})),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.output_text.delta":
        return ResponseOutputTextDeltaEvent(
            delta=data.get("delta", ""),
            content_index=data.get("content_index", 0),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.output_text.done":
        return ResponseOutputTextDoneEvent(
            text=data.get("text", ""),
            content_index=data.get("content_index", 0),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.function_call_arguments.delta":
        return ResponseFunctionCallArgumentsDeltaEvent(
            delta=data.get("delta", ""),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.function_call_arguments.done":
        return ResponseFunctionCallArgumentsDoneEvent(
            arguments=data.get("arguments", ""),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.reasoning_summary_text.delta":
        return ResponseReasoningSummaryTextDeltaEvent(
            delta=data.get("delta", ""),
            output_index=data.get("output_index", 0),
        )
    elif event_type == "response.reasoning_summary_text.done":
        return ResponseReasoningSummaryTextDoneEvent(
            text=data.get("text", ""),
            output_index=data.get("output_index", 0),
        )
    # Unknown event type — skip
    return None


def iter_sse_lines(text: str) -> Iterator[tuple[str, str]]:
    """Parse raw SSE text into (event_type, data_json) pairs."""
    event_type = ""
    data_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("event: "):
            event_type = line[7:].strip()
        elif line.startswith("data: "):
            data_lines.append(line[6:])
        elif line == "" and event_type:
            yield event_type, "\n".join(data_lines)
            event_type = ""
            data_lines = []

    # Yield any trailing event without a final blank line
    if event_type and data_lines:
        yield event_type, "\n".join(data_lines)


class ResponseStream:
    """Iterable of ResponseStreamEvent from an SSE response.

    Can be used as an iterator to process events one by one, or call
    ``get_final_response()`` to consume the stream and return the final Response.
    """

    def __init__(self, httpx_response: _HasText) -> None:
        self._response = httpx_response
        self._events: list[ResponseStreamEvent] = []
        self._final_response: Response | None = None
        self._consumed = False

    def __iter__(self) -> Iterator[ResponseStreamEvent]:
        if self._consumed:
            yield from self._events
            return

        self._consumed = True
        raw_text: str = self._response.text

        for event_type, data_str in iter_sse_lines(raw_text):
            try:
                data: dict[str, Any] = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            event = _parse_sse_event(event_type, data)
            if event is not None:
                self._events.append(event)

                if isinstance(event, (ResponseCompletedEvent, ResponseFailedEvent,
                                      ResponseIncompleteEvent)):
                    self._final_response = event.response

                yield event

    def get_final_response(self) -> Response:
        """Consume the entire stream and return the final Response."""
        if self._final_response is not None:
            return self._final_response

        # Consume remaining events
        for _ in self:
            pass

        if self._final_response is None:
            raise StreamError("Stream ended without a terminal event (completed/failed)")

        return self._final_response

    def __enter__(self) -> ResponseStream:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP response."""
        if hasattr(self._response, "close"):
            self._response.close()
