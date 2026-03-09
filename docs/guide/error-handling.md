# Error Handling

## Exception Hierarchy

All exceptions inherit from `CodexError`:

```
CodexError
├── APIError
│   ├── AuthError              — 401/403
│   ├── RateLimitError         — 429
│   ├── InvalidRequestError    — 400
│   │   └── ContextWindowError — input too long
│   ├── QuotaExceededError     — quota exhausted
│   └── ServerError            — 5xx
├── APIConnectionError         — network failure
│   └── APITimeoutError        — timeout
└── StreamError                — stream ended unexpectedly
```

## Catching Errors

```python
import codex_py

client = codex_py.CodexClient()

try:
    response = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Be helpful.",
        input="Hello!",
    )
except codex_py.RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except codex_py.AuthError as e:
    print(f"Auth failed ({e.status_code}): {e.message}")
    client.login()  # re-authenticate
except codex_py.ContextWindowError:
    print("Input too long — reduce context")
except codex_py.ServerError as e:
    print(f"Server error ({e.status_code}): {e.message}")
except codex_py.APIConnectionError as e:
    print(f"Network error: {e.message}")
except codex_py.CodexError as e:
    print(f"Unexpected error: {e}")
```

## Error Attributes

All `APIError` subclasses have:

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |
| `status_code` | `int` | HTTP status code |
| `code` | `str \| None` | Error code from the API (e.g. `"context_length_exceeded"`) |
| `body` | `object` | Raw response body |

`RateLimitError` also has:

| Attribute | Type | Description |
|-----------|------|-------------|
| `retry_after` | `float \| None` | Seconds to wait before retrying (parsed from error message) |

`APIConnectionError` has:

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Error description |
| `cause` | `BaseException \| None` | The underlying exception |

## Built-In Retries

The client automatically retries on `429` and `5xx` errors with exponential backoff:

```python
# Default: 2 retries
client = codex_py.CodexClient()

# More retries
client = codex_py.CodexClient(max_retries=5)

# No retries
client = codex_py.CodexClient(max_retries=0)
```

For `429` errors, the client uses the `retry_after` value from the error message if available, otherwise falls back to exponential backoff (1s, 2s, 4s, ...).

## Timeouts

```python
# Default timeout: 120 seconds
client = codex_py.CodexClient()

# Custom default timeout
client = codex_py.CodexClient(timeout=60.0)

# Per-request timeout
response = client.responses.create(
    ...,
    timeout=30.0,
)
```

Timeouts raise `APITimeoutError` (a subclass of `APIConnectionError`).
