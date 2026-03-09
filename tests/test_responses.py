"""Tests for _responses.py — input serialization and body building."""

from codex_py._responses import _serialize_dataclass, _serialize_input, _serialize_tool
from codex_py._types import FunctionCallOutput, FunctionTool, InputMessage, Reasoning, TextConfig


def test_serialize_string_input() -> None:
    result = _serialize_input("Hello")
    assert result == [{"role": "user", "content": "Hello"}]


def test_serialize_dict_input() -> None:
    items = [{"role": "user", "content": "Hi"}]
    result = _serialize_input(items)
    assert result == items


def test_serialize_typed_input() -> None:
    items = [InputMessage(role="user", content="Hi")]
    result = _serialize_input(items)
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hi"
    assert result[0]["type"] == "message"


def test_serialize_function_call_output() -> None:
    items = [FunctionCallOutput(call_id="call_1", output='{"temp":20}')]
    result = _serialize_input(items)
    assert result[0]["call_id"] == "call_1"
    assert result[0]["type"] == "function_call_output"


def test_serialize_mixed_input() -> None:
    items = [
        {"role": "user", "content": "Hi"},
        InputMessage(role="assistant", content="Hello!"),
    ]
    result = _serialize_input(items)
    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "Hi"}
    assert result[1]["role"] == "assistant"


def test_serialize_reasoning() -> None:
    r = Reasoning(effort="high", summary="detailed")
    d = _serialize_dataclass(r)
    assert d["effort"] == "high"
    assert d["summary"] == "detailed"


def test_serialize_reasoning_none_stripped() -> None:
    r = Reasoning(effort="low")
    d = _serialize_dataclass(r)
    assert d["effort"] == "low"
    assert "summary" not in d


def test_serialize_text_config() -> None:
    t = TextConfig(verbosity="medium")
    d = _serialize_dataclass(t)
    assert d["verbosity"] == "medium"


def test_serialize_tool_dataclass() -> None:
    tool = FunctionTool(
        name="f", description="d",
        parameters={"type": "object", "properties": {}},
    )
    d = _serialize_tool(tool)
    assert d["name"] == "f"
    assert d["type"] == "function"
    assert d["strict"] is True


def test_serialize_tool_dict() -> None:
    tool = {"type": "function", "name": "f"}
    assert _serialize_tool(tool) is tool


def test_serialize_dataclass_dict_passthrough() -> None:
    d = {"key": "value"}
    assert _serialize_dataclass(d) is d
