"""Tests for _types.py data models."""

from codex_open_client._types import (
    FunctionTool,
    InputMessage,
    OutputText,
    Reasoning,
    ReasoningSummary,
    Response,
    ResponseFormatJsonObject,
    ResponseFormatJsonSchema,
    ResponseFormatText,
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseReasoningItem,
    TextConfig,
    Usage,
)


def test_response_output_text() -> None:
    resp = Response(
        id="resp_1",
        model="gpt-5.1-codex-mini",
        output=[
            ResponseOutputMessage(
                id="msg_1",
                content=[OutputText(text="Hello "), OutputText(text="world!")],
            ),
        ],
    )
    assert resp.output_text == "Hello world!"


def test_response_output_text_empty() -> None:
    resp = Response(id="resp_1", model="m", output=[])
    assert resp.output_text == ""


def test_response_reasoning_summary() -> None:
    resp = Response(
        id="resp_1",
        model="m",
        output=[
            ResponseReasoningItem(
                id="r_1",
                summary=[
                    ReasoningSummary(text="Step 1"),
                    ReasoningSummary(text="Step 2"),
                ],
            ),
        ],
    )
    assert resp.reasoning_summary == "Step 1\nStep 2"


def test_response_reasoning_summary_none() -> None:
    resp = Response(id="resp_1", model="m", output=[])
    assert resp.reasoning_summary is None


def test_response_tool_calls() -> None:
    call = ResponseFunctionToolCall(
        call_id="call_1", name="get_weather", arguments='{"city":"Tokyo"}'
    )
    resp = Response(
        id="resp_1",
        model="m",
        output=[
            ResponseOutputMessage(id="msg_1", content=[]),
            call,
        ],
    )
    assert resp.tool_calls == [call]


def test_response_tool_calls_empty() -> None:
    resp = Response(id="resp_1", model="m", output=[])
    assert resp.tool_calls == []


def test_input_message_defaults() -> None:
    msg = InputMessage(role="user", content="hi")
    assert msg.type == "message"


def test_function_tool_defaults() -> None:
    tool = FunctionTool(name="f", description="d", parameters={})
    assert tool.strict is True
    assert tool.type == "function"


def test_reasoning_defaults() -> None:
    r = Reasoning()
    assert r.effort is None
    assert r.summary is None


def test_usage_fields() -> None:
    u = Usage(input_tokens=10, output_tokens=20, total_tokens=30)
    assert u.total_tokens == 30


def test_response_format_text_defaults() -> None:
    fmt = ResponseFormatText()
    assert fmt.type == "text"


def test_response_format_json_object_defaults() -> None:
    fmt = ResponseFormatJsonObject()
    assert fmt.type == "json_object"


def test_response_format_json_schema() -> None:
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    fmt = ResponseFormatJsonSchema(name="person", schema=schema, strict=True)
    assert fmt.type == "json_schema"
    assert fmt.name == "person"
    assert fmt.schema == schema
    assert fmt.strict is True
    assert fmt.description is None


def test_text_config_with_format() -> None:
    fmt = ResponseFormatJsonSchema(
        name="person",
        schema={"type": "object", "properties": {"name": {"type": "string"}}},
        strict=True,
    )
    cfg = TextConfig(format=fmt)
    assert cfg.format == fmt
    assert cfg.verbosity is None


def test_text_config_defaults() -> None:
    cfg = TextConfig()
    assert cfg.format is None
    assert cfg.verbosity is None
