# Errors

## Hierarchy

```
CodexError
├── APIError
│   ├── AuthError
│   ├── RateLimitError
│   ├── InvalidRequestError
│   │   └── ContextWindowError
│   ├── QuotaExceededError
│   └── ServerError
├── APIConnectionError
│   └── APITimeoutError
└── StreamError
```

## Base Classes

::: codex_open_client.CodexError

::: codex_open_client.APIError

::: codex_open_client.APIConnectionError

## API Errors

::: codex_open_client.AuthError

::: codex_open_client.RateLimitError

::: codex_open_client.InvalidRequestError

::: codex_open_client.ContextWindowError

::: codex_open_client.QuotaExceededError

::: codex_open_client.ServerError

## Connection Errors

::: codex_open_client.APITimeoutError

## Stream Errors

::: codex_open_client.StreamError
