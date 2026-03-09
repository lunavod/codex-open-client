# Getting Started

## Installation

```bash
pip install codex-open-client
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add codex-open-client
```

## First Login

When you create a `CodexClient` for the first time, it opens your browser for OAuth authentication:

```python
import codex_open_client

client = codex_open_client.CodexClient()
```

1. Your browser opens the OpenAI login page
2. Sign in with your ChatGPT account
3. Click "Continue" to authorize
4. The browser redirects to `localhost:1455` — the library catches the callback
5. Tokens are saved to `~/.codex/auth.json`

On subsequent runs, cached tokens are reused automatically. When they expire, the refresh token handles renewal — no re-login needed.

## Your First Request

```python
import codex_open_client

client = codex_open_client.CodexClient()

response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are a helpful assistant.",
    input="Explain Python decorators in one sentence.",
)

print(response.output_text)
```

## Streaming

Stream responses to see output as it arrives:

```python
with client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be helpful.",
    input="Write a haiku about Python.",
    stream=True,
) as stream:
    for event in stream:
        if isinstance(event, codex_open_client.ResponseOutputTextDeltaEvent):
            print(event.delta, end="", flush=True)
    print()
```

## Listing Models

```python
models = client.models.list()
for m in models:
    print(f"{m.slug} (context: {m.context_window})")
```

## What's Next

- [Authentication](guide/authentication.md) — headless mode, custom handlers, two-step login
- [Responses](guide/responses.md) — multi-turn, reasoning, all parameters
- [Structured Output](guide/structured-output.md) — Pydantic models, JSON schemas
- [Tool Calls](guide/tool-calls.md) — function calling and roundtrips
- [Error Handling](guide/error-handling.md) — retries, rate limits, exception types
