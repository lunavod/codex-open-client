"""Tests for _stream.py SSE parsing and ResponseStream."""

from typing import Any

import pytest

from codex_open_client._errors import StreamError
from codex_open_client._stream import (
    ResponseStream,
    _parse_response,
    _parse_sse_event,
    iter_sse_lines,
)
from codex_open_client._types import (
    ResponseCompletedEvent,
    ResponseCreatedEvent,
    ResponseFailedEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseIncompleteEvent,
    ResponseInProgressEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputTextDeltaEvent,
    ResponseOutputTextDoneEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
)


def test_parse_response_basic() -> None:
    data: dict[str, Any] = {
        "id": "resp_123",
        "model": "gpt-5.1-codex-mini",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Hello!"}],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }
    resp = _parse_response(data)
    assert resp.id == "resp_123"
    assert resp.model == "gpt-5.1-codex-mini"
    assert resp.status == "completed"
    assert resp.output_text == "Hello!"
    assert resp.usage is not None
    assert resp.usage.total_tokens == 15


def test_parse_response_with_tool_call() -> None:
    data: dict[str, Any] = {
        "id": "resp_1",
        "model": "m",
        "output": [
            {
                "type": "function_call",
                "call_id": "call_1",
                "name": "get_weather",
                "arguments": '{"city":"NYC"}',
                "status": "completed",
            }
        ],
    }
    resp = _parse_response(data)
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "get_weather"
    assert resp.tool_calls[0].arguments == '{"city":"NYC"}'


def test_parse_response_with_reasoning() -> None:
    data: dict[str, Any] = {
        "id": "resp_1",
        "model": "m",
        "output": [
            {
                "type": "reasoning",
                "id": "r_1",
                "summary": [{"type": "summary_text", "text": "Thinking..."}],
            }
        ],
    }
    resp = _parse_response(data)
    assert resp.reasoning_summary == "Thinking..."


def test_iter_sse_lines() -> None:
    raw = (
        "event: response.created\n"
        'data: {"id":"resp_1"}\n'
        "\n"
        "event: response.output_text.delta\n"
        'data: {"delta":"Hi"}\n'
        "\n"
    )
    events = list(iter_sse_lines(raw))
    assert len(events) == 2
    assert events[0][0] == "response.created"
    assert events[1][0] == "response.output_text.delta"


def test_iter_sse_lines_trailing_event() -> None:
    """An event at the end without a trailing blank line should still be yielded."""
    raw = (
        "event: response.completed\n"
        'data: {"response":{"id":"r","model":"m","output":[]}}\n'
    )
    events = list(iter_sse_lines(raw))
    assert len(events) == 1


def test_parse_sse_event_text_delta() -> None:
    event = _parse_sse_event("response.output_text.delta", {"delta": "Hello"})
    assert isinstance(event, ResponseOutputTextDeltaEvent)
    assert event.delta == "Hello"


def test_parse_sse_event_text_done() -> None:
    event = _parse_sse_event("response.output_text.done", {"text": "Full text"})
    assert isinstance(event, ResponseOutputTextDoneEvent)
    assert event.text == "Full text"


def test_parse_sse_event_function_call_delta() -> None:
    event = _parse_sse_event(
        "response.function_call_arguments.delta", {"delta": '{"ci'}
    )
    assert isinstance(event, ResponseFunctionCallArgumentsDeltaEvent)


def test_parse_sse_event_function_call_done() -> None:
    event = _parse_sse_event(
        "response.function_call_arguments.done", {"arguments": '{"city":"NYC"}'}
    )
    assert isinstance(event, ResponseFunctionCallArgumentsDoneEvent)
    assert event.arguments == '{"city":"NYC"}'


def test_parse_sse_event_reasoning_delta() -> None:
    event = _parse_sse_event(
        "response.reasoning_summary_text.delta", {"delta": "Step 1"}
    )
    assert isinstance(event, ResponseReasoningSummaryTextDeltaEvent)


def test_parse_sse_event_in_progress() -> None:
    data: dict[str, Any] = {
        "response": {"id": "resp_1", "model": "m", "output": [], "status": None}
    }
    event = _parse_sse_event("response.in_progress", data)
    assert isinstance(event, ResponseInProgressEvent)
    assert event.response.id == "resp_1"


def test_parse_sse_event_failed() -> None:
    data: dict[str, Any] = {
        "response": {"id": "resp_1", "model": "m", "output": [], "status": "failed"}
    }
    event = _parse_sse_event("response.failed", data)
    assert isinstance(event, ResponseFailedEvent)
    assert event.response.status == "failed"


def test_parse_sse_event_incomplete() -> None:
    data: dict[str, Any] = {
        "response": {
            "id": "resp_1", "model": "m", "output": [],
            "status": "incomplete",
        }
    }
    event = _parse_sse_event("response.incomplete", data)
    assert isinstance(event, ResponseIncompleteEvent)


def test_parse_sse_event_output_item_added() -> None:
    data: dict[str, Any] = {
        "item": {"type": "message", "id": "msg_1", "role": "assistant", "content": []},
        "output_index": 0,
    }
    event = _parse_sse_event("response.output_item.added", data)
    assert isinstance(event, ResponseOutputItemAddedEvent)
    assert event.output_index == 0


def test_parse_sse_event_output_item_done() -> None:
    data: dict[str, Any] = {
        "item": {
            "type": "message", "id": "msg_1", "role": "assistant",
            "content": [{"type": "output_text", "text": "Done"}],
        },
        "output_index": 0,
    }
    event = _parse_sse_event("response.output_item.done", data)
    assert isinstance(event, ResponseOutputItemDoneEvent)
    assert event.output_index == 0


def test_parse_sse_event_reasoning_done() -> None:
    event = _parse_sse_event(
        "response.reasoning_summary_text.done", {"text": "Full reasoning"}
    )
    assert isinstance(event, ResponseReasoningSummaryTextDoneEvent)
    assert event.text == "Full reasoning"


def test_parse_sse_event_unknown() -> None:
    event = _parse_sse_event("response.unknown_event", {})
    assert event is None


def test_parse_sse_event_created() -> None:
    data: dict[str, Any] = {
        "response": {"id": "resp_1", "model": "m", "output": [], "status": None}
    }
    event = _parse_sse_event("response.created", data)
    assert isinstance(event, ResponseCreatedEvent)
    assert event.response.id == "resp_1"


class _FakeResponse:
    """Fake httpx.Response for testing ResponseStream."""

    def __init__(self, text: str) -> None:
        self.text = text


def test_response_stream_collect() -> None:
    import json

    completed_data = json.dumps({
        "response": {
            "id": "r1", "model": "m", "status": "completed",
            "output": [{"type": "message", "id": "msg_1", "role": "assistant",
                        "content": [{"type": "output_text", "text": "Hi"}]}],
            "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
        }
    })
    sse = (
        "event: response.created\n"
        'data: {"response":{"id":"r1","model":"m","output":[],"status":null}}\n'
        "\n"
        "event: response.output_text.delta\n"
        'data: {"delta":"Hi"}\n'
        "\n"
        "event: response.completed\n"
        f"data: {completed_data}\n"
        "\n"
    )
    stream = ResponseStream(_FakeResponse(sse))
    resp = stream.get_final_response()
    assert resp.id == "r1"
    assert resp.output_text == "Hi"
    assert resp.usage is not None
    assert resp.usage.total_tokens == 7


def test_response_stream_iterate() -> None:
    sse = (
        "event: response.created\n"
        'data: {"response":{"id":"r1","model":"m","output":[]}}\n'
        "\n"
        "event: response.output_text.delta\n"
        'data: {"delta":"A"}\n'
        "\n"
        "event: response.output_text.delta\n"
        'data: {"delta":"B"}\n'
        "\n"
        "event: response.completed\n"
        'data: {"response":{"id":"r1","model":"m","output":[],"status":"completed"}}\n'
        "\n"
    )
    stream = ResponseStream(_FakeResponse(sse))
    events = list(stream)
    assert len(events) == 4
    assert isinstance(events[0], ResponseCreatedEvent)
    assert isinstance(events[1], ResponseOutputTextDeltaEvent)
    assert events[1].delta == "A"
    assert isinstance(events[3], ResponseCompletedEvent)


def test_response_stream_no_terminal_event() -> None:
    sse = (
        "event: response.created\n"
        'data: {"response":{"id":"r1","model":"m","output":[]}}\n'
        "\n"
    )
    stream = ResponseStream(_FakeResponse(sse))
    with pytest.raises(StreamError, match="terminal event"):
        stream.get_final_response()


def test_response_stream_close() -> None:
    """close() should call close on the underlying response."""
    closed = False

    class _ClosableResponse:
        text = (
            "event: response.completed\n"
            'data: {"response":{"id":"r1","model":"m","output":[],'
            '"status":"completed"}}\n'
            "\n"
        )

        def close(self) -> None:
            nonlocal closed
            closed = True

    stream = ResponseStream(_ClosableResponse())
    stream.close()
    assert closed


def test_response_stream_failed_event() -> None:
    """A failed stream should still return the response via get_final_response."""
    sse = (
        "event: response.failed\n"
        'data: {"response":{"id":"r1","model":"m","output":[],'
        '"status":"failed"}}\n'
        "\n"
    )
    stream = ResponseStream(_FakeResponse(sse))
    resp = stream.get_final_response()
    assert resp.status == "failed"


def test_response_stream_reiter() -> None:
    """Iterating a consumed stream should replay cached events."""
    sse = (
        "event: response.completed\n"
        'data: {"response":{"id":"r1","model":"m","output":[],"status":"completed"}}\n'
        "\n"
    )
    stream = ResponseStream(_FakeResponse(sse))
    first = list(stream)
    second = list(stream)
    assert len(first) == len(second)
