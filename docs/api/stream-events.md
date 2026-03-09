# Stream Events

All stream events are dataclasses with a `type` field matching the SSE event name.

Use `isinstance()` checks to handle specific event types when iterating a `ResponseStream`.

## Response Lifecycle Events

::: codex_py.ResponseCreatedEvent

::: codex_py.ResponseInProgressEvent

::: codex_py.ResponseCompletedEvent

::: codex_py.ResponseFailedEvent

::: codex_py.ResponseIncompleteEvent

## Text Events

::: codex_py.ResponseOutputTextDeltaEvent

::: codex_py.ResponseOutputTextDoneEvent

## Output Item Events

::: codex_py.ResponseOutputItemAddedEvent

::: codex_py.ResponseOutputItemDoneEvent

## Function Call Events

::: codex_py.ResponseFunctionCallArgumentsDeltaEvent

::: codex_py.ResponseFunctionCallArgumentsDoneEvent

## Reasoning Events

::: codex_py.ResponseReasoningSummaryTextDeltaEvent

::: codex_py.ResponseReasoningSummaryTextDoneEvent
