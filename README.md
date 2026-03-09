# codex-open-client

[![PyPI](https://img.shields.io/pypi/v/codex-open-client)](https://pypi.org/project/codex-open-client/)
[![Python](https://img.shields.io/pypi/pyversions/codex-open-client)](https://pypi.org/project/codex-open-client/)
[![License](https://img.shields.io/github/license/lunavod/codex-open-client)](LICENSE)
[![CI](https://github.com/lunavod/codex-open-client/actions/workflows/ci.yml/badge.svg)](https://github.com/lunavod/codex-open-client/actions/workflows/ci.yml)

Python client for OpenAI Codex — use your ChatGPT Plus/Pro subscription for API access.

**[Documentation](https://lunavod.github.io/codex-open-client/)**

## Installation

```bash
pip install codex-open-client
```

## Quick Start

```python
import codex_open_client

client = codex_open_client.CodexClient()

response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input="What is 2 + 2?",
)
print(response.output_text)
```

On first run, your browser opens for OAuth login. Tokens are cached at `~/.codex/auth.json` (shared with the official Codex CLI) and refreshed automatically after that.

## Authentication

Multiple ways to authenticate, depending on your environment:

```python
# Default — opens browser, local server catches the callback
client = codex_open_client.CodexClient()

# Headless — prints URL, you paste the redirect URL back (servers, Docker, CI)
client = codex_open_client.CodexClient(headless=True)

# Custom handler — full control over the auth UX (GUI apps, bots, web apps)
def my_handler(url: str) -> str:
    send_url_to_user(url)
    return get_callback_url_from_user()

client = codex_open_client.CodexClient(login_handler=my_handler)
```

For async or multi-step flows, use the two-step API:

```python
auth = codex_open_client.start_login()
# present auth.url to the user, collect callback URL however you want
tokens = codex_open_client.finish_login(auth, callback_url="http://localhost:1455/...")
```

## Streaming

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

## Tool Calls

```python
import json

tool = codex_open_client.FunctionTool(
    name="get_weather",
    description="Get weather for a city.",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    },
)

response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Use tools when helpful.",
    input="What's the weather in Tokyo?",
    tools=[tool],
)

for call in response.tool_calls:
    print(f"{call.name}({call.arguments})")
```

## Structured Output

Get typed responses using Pydantic models:

```bash
pip install codex-open-client[pydantic]
```

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int
    city: str

parsed = client.responses.parse(
    model="gpt-5.1-codex-mini",
    instructions="Extract the person info.",
    input="John Smith is 30 years old and lives in New York.",
    text_format=Person,
)

print(parsed.output_parsed.name)  # "John Smith"
print(parsed.output_parsed.age)   # 30
```

Also works with manual JSON schema via `TextConfig` and `ResponseFormatJsonSchema` — see the [docs](https://lunavod.github.io/codex-open-client/).

## Features

- **Automatic auth** — OAuth PKCE with token caching and refresh
- **Typed API** — dataclass-based types for all objects, full mypy strict support
- **Structured output** — `parse()` with Pydantic models or manual JSON schemas
- **Streaming** — iterate SSE events with context manager support
- **Tool calls** — function calling with roundtrip helpers
- **Retries** — built-in exponential backoff for 429/5xx
- **Models** — list available models with cached metadata
- **Headless mode** — works on remote servers, Docker, CI
- **Custom login** — bring your own auth UX with `login_handler`
- **CLI interop** — shares token storage with the official Codex CLI

## Requirements

- Python 3.10+
- ChatGPT Plus or Pro subscription

## License

MIT
