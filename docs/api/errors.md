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

::: codex_py.CodexError

::: codex_py.APIError

::: codex_py.APIConnectionError

## API Errors

::: codex_py.AuthError

::: codex_py.RateLimitError

::: codex_py.InvalidRequestError

::: codex_py.ContextWindowError

::: codex_py.QuotaExceededError

::: codex_py.ServerError

## Connection Errors

::: codex_py.APITimeoutError

## Stream Errors

::: codex_py.StreamError
