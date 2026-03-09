# Responses

The `client.responses.create()` method is the main way to interact with the Codex API.

## Basic Usage

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are a helpful assistant.",
    input="Hello!",
)

print(response.output_text)    # joined text from all output messages
print(response.usage)          # Usage(input_tokens=..., output_tokens=..., total_tokens=...)
```

## Parameters

### Required

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `str` | Model slug (e.g. `"gpt-5.1-codex-mini"`) |
| `instructions` | `str` | System instructions for the model |
| `input` | `str` or `list` | User message string or list of input items |

### Optional

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stream` | `bool` | `False` | Return a `ResponseStream` instead of `Response` |
| `tools` | `list[FunctionTool]` | `None` | Function tools the model can call |
| `tool_choice` | `str` | `None` | `"auto"`, `"none"`, or `"required"` |
| `parallel_tool_calls` | `bool` | `None` | Allow parallel tool calls |
| `reasoning` | `Reasoning` | `None` | Extended thinking configuration |
| `text` | `TextConfig` | `None` | Text output config ([structured output](structured-output.md)) |
| `service_tier` | `str` | `None` | `"auto"`, `"flex"`, or `"priority"` |
| `timeout` | `float` | Client default | Per-request timeout in seconds |

## Multi-Turn Conversations

Pass previous output items back as input for multi-turn:

```python
response1 = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are helpful.",
    input="My name is Alice.",
)

response2 = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are helpful.",
    input=[
        codex_open_client.InputMessage(role="user", content="My name is Alice."),
        *response1.output,
        codex_open_client.InputMessage(role="user", content="What's my name?"),
    ],
)
print(response2.output_text)  # "Your name is Alice."
```

!!! warning "Filter reasoning items in multi-turn"
    When feeding output back as input, filter out `ResponseReasoningItem` objects.
    They have server-side IDs that can't be referenced with `store=false`:

    ```python
    input_items = [
        item for item in response.output
        if not isinstance(item, codex_open_client.ResponseReasoningItem)
    ]
    ```

## Dict-Based Input

You can also pass raw dicts instead of typed objects:

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ],
)
```

## Reasoning

Enable extended thinking with the `reasoning` parameter:

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Think step by step.",
    input="What is 15% of 847?",
    reasoning=codex_open_client.Reasoning(effort="high", summary="auto"),
)

print(response.reasoning_summary)  # summary of the thinking process
print(response.output_text)        # final answer
```

## Structured Output

See the dedicated [Structured Output](structured-output.md) guide for:

- **`parse()`** — pass a Pydantic model, get a typed `ParsedResponse[T]` back
- **`ResponseFormatJsonSchema`** — manual JSON schema constraints
- **`ResponseFormatJsonObject`** — free-form JSON mode

## Response Object

The `Response` object has convenience properties:

| Property | Type | Description |
|----------|------|-------------|
| `output_text` | `str` | All text content joined |
| `reasoning_summary` | `str \| None` | All reasoning summaries joined |
| `tool_calls` | `list[ResponseFunctionToolCall]` | All tool calls extracted |
| `output` | `list[OutputItem]` | Raw output items |
| `usage` | `Usage \| None` | Token counts |
| `status` | `str \| None` | `"completed"`, `"failed"`, or `"incomplete"` |
