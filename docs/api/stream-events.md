# Stream Events

All stream events are dataclasses with a `type` field matching the SSE event name.

Use `isinstance()` checks to handle specific event types when iterating a `ResponseStream`.

## Response Lifecycle Events

::: codex_open_client.ResponseCreatedEvent

::: codex_open_client.ResponseInProgressEvent

::: codex_open_client.ResponseCompletedEvent

::: codex_open_client.ResponseFailedEvent

::: codex_open_client.ResponseIncompleteEvent

## Text Events

::: codex_open_client.ResponseOutputTextDeltaEvent

::: codex_open_client.ResponseOutputTextDoneEvent

## Output Item Events

::: codex_open_client.ResponseOutputItemAddedEvent

::: codex_open_client.ResponseOutputItemDoneEvent

## Function Call Events

::: codex_open_client.ResponseFunctionCallArgumentsDeltaEvent

::: codex_open_client.ResponseFunctionCallArgumentsDoneEvent

## Reasoning Events

::: codex_open_client.ResponseReasoningSummaryTextDeltaEvent

::: codex_open_client.ResponseReasoningSummaryTextDoneEvent
