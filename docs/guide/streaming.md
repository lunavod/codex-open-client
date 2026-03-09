# Streaming

When `stream=True`, `create()` returns a `ResponseStream` that yields events as they arrive from the API.

## Basic Streaming

```python
with client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be helpful.",
    input="Tell me a joke.",
    stream=True,
) as stream:
    for event in stream:
        if isinstance(event, codex_py.ResponseOutputTextDeltaEvent):
            print(event.delta, end="", flush=True)
    print()
```

## Getting the Final Response

You can consume the stream and get the complete `Response`:

```python
stream = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input="Hello!",
    stream=True,
)

response = stream.get_final_response()
print(response.output_text)
```

## Re-Iterating

A consumed stream caches its events. You can iterate again:

```python
stream = client.responses.create(..., stream=True)

# First pass — print deltas
for event in stream:
    if isinstance(event, codex_py.ResponseOutputTextDeltaEvent):
        print(event.delta, end="")

# Second pass — count events (uses cached events, no network)
event_count = sum(1 for _ in stream)
```

## Event Types

All events are dataclasses with a `type` field. Use `isinstance()` to filter:

### Text Events

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `ResponseOutputTextDeltaEvent` | `delta: str` | A chunk of text output |
| `ResponseOutputTextDoneEvent` | `text: str` | Complete text for one content block |

### Response Lifecycle

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `ResponseCreatedEvent` | `response` | Response object created |
| `ResponseInProgressEvent` | `response` | Model is generating |
| `ResponseCompletedEvent` | `response` | Response finished successfully |
| `ResponseFailedEvent` | `response` | Response failed |
| `ResponseIncompleteEvent` | `response` | Response was cut short |

### Output Items

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `ResponseOutputItemAddedEvent` | `item`, `output_index` | New output item started |
| `ResponseOutputItemDoneEvent` | `item`, `output_index` | Output item completed |

### Tool Calls

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `ResponseFunctionCallArgumentsDeltaEvent` | `delta` | Chunk of function arguments |
| `ResponseFunctionCallArgumentsDoneEvent` | `arguments` | Complete function arguments |

### Reasoning

| Event | Key Fields | Description |
|-------|-----------|-------------|
| `ResponseReasoningSummaryTextDeltaEvent` | `delta` | Chunk of reasoning summary |
| `ResponseReasoningSummaryTextDoneEvent` | `text` | Complete reasoning summary |

See [Stream Events API Reference](../api/stream-events.md) for full type details.

## Context Manager

`ResponseStream` supports `with` statements to ensure the underlying HTTP response is closed:

```python
with client.responses.create(..., stream=True) as stream:
    for event in stream:
        ...
# HTTP response is closed here
```
