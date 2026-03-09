"""Live tests for CodexClient that hit the real Codex API.

Never run by default. Run explicitly with:
    pytest -m live
"""

import pytest

import codex_open_client
from codex_open_client._config import DEFAULT_TOKEN_PATH, load_tokens

pytestmark = pytest.mark.live


@pytest.fixture()
def client() -> codex_open_client.CodexClient:
    """Create a real CodexClient, skipping if no cached credentials."""
    tokens = load_tokens(DEFAULT_TOKEN_PATH)
    if tokens is None:
        pytest.skip("No cached tokens in ~/.codex/auth.json")
    return codex_open_client.CodexClient(token_path=DEFAULT_TOKEN_PATH)


def test_client_creates(client: codex_open_client.CodexClient) -> None:
    assert isinstance(client, codex_open_client.CodexClient)
    assert client.token
    assert client.account_id


def test_models_list(client: codex_open_client.CodexClient) -> None:
    models = client.models.list()
    assert len(models) > 0
    assert isinstance(models[0], codex_open_client.Model)
    assert models[0].slug
    assert models[0].display_name


def test_models_have_context_window(client: codex_open_client.CodexClient) -> None:
    models = client.models.list()
    has_ctx = any(m.context_window is not None for m in models)
    assert has_ctx, "At least one model should have context_window"


def test_models_cache(client: codex_open_client.CodexClient) -> None:
    """Second call should return cached results."""
    m1 = client.models.list()
    m2 = client.models.list()
    assert m1 == m2


def test_simple_response(client: codex_open_client.CodexClient) -> None:
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="You are a helpful assistant. Be brief.",
        input="Reply with exactly one word: pong",
    )
    assert isinstance(response, codex_open_client.Response)
    assert response.id
    assert response.status == "completed"
    assert "pong" in response.output_text.lower()


def test_simple_response_usage(client: codex_open_client.CodexClient) -> None:
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input="Say hi",
    )
    assert response.usage is not None
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0


def test_streaming_response(client: codex_open_client.CodexClient) -> None:
    stream = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input="Reply with exactly: hello",
        stream=True,
    )

    events = list(stream)
    assert len(events) > 0

    # Should have created and completed events
    event_types = [e.type for e in events]
    assert "response.created" in event_types
    assert "response.completed" in event_types

    # Should be able to get final response
    resp = stream.get_final_response()
    assert isinstance(resp, codex_open_client.Response)


def test_streaming_text_deltas(client: codex_open_client.CodexClient) -> None:
    stream = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input="Count from 1 to 5",
        stream=True,
    )

    deltas: list[str] = []
    for event in stream:
        if isinstance(event, codex_open_client.ResponseOutputTextDeltaEvent):
            deltas.append(event.delta)

    assert len(deltas) > 0, "Should have received text deltas"
    full_text = "".join(deltas)
    assert len(full_text) > 0


def test_multi_turn(client: codex_open_client.CodexClient) -> None:
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input=[
            codex_open_client.InputMessage(role="user", content="My name is Alice."),
            codex_open_client.InputMessage(role="assistant", content="Nice to meet you, Alice!"),
            codex_open_client.InputMessage(role="user", content="What is my name?"),
        ],
    )
    assert "alice" in response.output_text.lower()


def test_dict_input(client: codex_open_client.CodexClient) -> None:
    """Dict-based input should work alongside typed InputMessage."""
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be brief.",
        input=[{"role": "user", "content": "Reply with exactly: ok"}],
    )
    assert "ok" in response.output_text.lower()


def test_reasoning(client: codex_open_client.CodexClient) -> None:
    """Reasoning parameter should produce a reasoning summary."""
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Think step by step.",
        input="What is 17 * 23?",
        reasoning=codex_open_client.Reasoning(effort="low"),
    )
    assert response.status == "completed"
    assert response.output_text
    assert "391" in response.output_text


def test_models_fields(client: codex_open_client.CodexClient) -> None:
    """Model objects should have the rich metadata fields."""
    models = client.models.list()
    # At least one model should have reasoning levels
    has_reasoning = any(len(m.reasoning_levels) > 0 for m in models)
    assert has_reasoning, "Expected at least one model with reasoning_levels"
    # At least one model should have input modalities
    has_modalities = any(len(m.input_modalities) > 0 for m in models)
    assert has_modalities, "Expected at least one model with input_modalities"


def test_models_force_refresh(client: codex_open_client.CodexClient) -> None:
    """force_refresh should bypass the cache."""
    m1 = client.models.list()
    m2 = client.models.list(force_refresh=True)
    # Both should return valid data (not asserting inequality since data is the same)
    assert len(m1) > 0
    assert len(m2) > 0


def test_tool_call(client: codex_open_client.CodexClient) -> None:
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Always use the get_weather tool when asked about weather.",
        input="What's the weather in Tokyo?",
        tools=[
            codex_open_client.FunctionTool(
                name="get_weather",
                description="Get the weather for a city",
                parameters={
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                    "additionalProperties": False,
                },
            ),
        ],
    )
    assert len(response.tool_calls) > 0
    call = response.tool_calls[0]
    assert call.name == "get_weather"
    assert "tokyo" in call.arguments.lower() or "Tokyo" in call.arguments


def test_tool_call_roundtrip(client: codex_open_client.CodexClient) -> None:
    """Full tool call loop: request → tool_call → FunctionCallOutput → answer."""
    tool = codex_open_client.FunctionTool(
        name="add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    )

    # Step 1: Ask something that requires the tool
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Always use the add tool to add numbers. Never calculate yourself.",
        input="What is 3 + 7?",
        tools=[tool],
    )

    assert len(response.tool_calls) > 0
    call = response.tool_calls[0]
    assert call.name == "add"

    # Step 2: Feed the result back (filter out reasoning items — they have
    # server-side IDs that can't be referenced with store=false)
    output_no_reasoning = [
        item for item in response.output
        if not isinstance(item, codex_open_client.ResponseReasoningItem)
    ]
    response2 = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Always use the add tool to add numbers. Never calculate yourself.",
        input=[
            codex_open_client.InputMessage(role="user", content="What is 3 + 7?"),
            *output_no_reasoning,
            codex_open_client.FunctionCallOutput(call_id=call.call_id, output="10"),
        ],
        tools=[tool],
    )

    assert response2.status == "completed"
    assert "10" in response2.output_text
