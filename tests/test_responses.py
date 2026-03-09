"""Tests for _responses.py — input serialization and body building."""

from codex_open_client._responses import (
    _ensure_strict_schema,
    _pydantic_to_format,
    _serialize_dataclass,
    _serialize_input,
    _serialize_tool,
)
from codex_open_client._types import (
    FunctionCallOutput,
    FunctionTool,
    InputMessage,
    Reasoning,
    ResponseFormatJsonSchema,
    TextConfig,
)


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


def test_serialize_text_config_with_json_schema() -> None:
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
        "additionalProperties": False,
    }
    cfg = TextConfig(
        format=ResponseFormatJsonSchema(name="person", schema=schema, strict=True),
    )
    d = _serialize_dataclass(cfg)
    assert d == {
        "format": {
            "name": "person",
            "schema": schema,
            "type": "json_schema",
            "strict": True,
        },
    }
    # description=None should be stripped
    assert "description" not in d["format"]
    # verbosity=None should be stripped
    assert "verbosity" not in d


def test_ensure_strict_schema_adds_additional_properties() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
            },
        },
    }
    result = _ensure_strict_schema(schema)
    assert result["additionalProperties"] is False
    assert result["properties"]["address"]["additionalProperties"] is False


def test_ensure_strict_schema_preserves_existing() -> None:
    schema = {"type": "object", "additionalProperties": True, "properties": {}}
    result = _ensure_strict_schema(schema)
    # Should not override existing value
    assert result["additionalProperties"] is True


def test_ensure_strict_schema_handles_arrays() -> None:
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
        },
    }
    result = _ensure_strict_schema(schema)
    assert result["items"]["additionalProperties"] is False


def test_ensure_strict_schema_handles_defs() -> None:
    schema = {
        "type": "object",
        "properties": {},
        "$defs": {
            "Inner": {
                "type": "object",
                "properties": {"v": {"type": "string"}},
            },
        },
    }
    result = _ensure_strict_schema(schema)
    assert result["$defs"]["Inner"]["additionalProperties"] is False


def test_pydantic_to_format() -> None:
    pytest = __import__("pytest")
    try:
        from pydantic import BaseModel
    except ImportError:
        pytest.skip("pydantic not installed")

    class City(BaseModel):
        name: str
        population: int

    fmt = _pydantic_to_format(City)
    assert fmt.name == "City"
    assert fmt.type == "json_schema"
    assert fmt.strict is True
    assert fmt.schema["type"] == "object"
    assert "name" in fmt.schema["properties"]
    assert "population" in fmt.schema["properties"]
    assert fmt.schema["additionalProperties"] is False


def test_pydantic_to_format_rejects_non_pydantic() -> None:
    with __import__("pytest").raises(TypeError, match="not a Pydantic BaseModel"):
        _pydantic_to_format(dict)
