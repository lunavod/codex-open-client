# codex-py

**Python client for OpenAI Codex** — use your ChatGPT Plus/Pro subscription for API access.

`codex-py` handles OAuth authentication, token management, and provides a typed Python interface to the Codex API at `chatgpt.com/backend-api/codex`.

## Quick Example

```python
import codex_py

client = codex_py.CodexClient()

response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input="What is 2 + 2?",
)
print(response.output_text)
```

## Features

- **Automatic authentication** — OAuth PKCE flow with token caching and refresh
- **Typed responses** — dataclass-based types for all API objects
- **Streaming** — iterate over server-sent events as they arrive
- **Tool calls** — define functions, handle tool call roundtrips
- **Retry logic** — built-in retry with exponential backoff for 429/5xx
- **Models endpoint** — list available models with cached metadata

## Requirements

- Python 3.10+
- A ChatGPT Plus or Pro subscription

## Next Steps

- [Getting Started](getting-started.md) — install, authenticate, make your first request
- [Guide](guide/authentication.md) — detailed walkthroughs for each feature
- [API Reference](api/client.md) — full class and type documentation
