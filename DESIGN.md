# codex-py — Client Design

Follows the OpenAI Python SDK patterns closely (`@overload` for stream typing,
discriminated unions for output items, Pydantic-style typed models) so users
familiar with `openai.OpenAI()` can adopt this with minimal friction.

## Construction

```python
import codex_py

# Auto-login, auto-refresh, reads ~/.codex/auth.json
client = codex_py.CodexClient()

# Headless/remote
client = codex_py.CodexClient(headless=True)

# Custom token path
client = codex_py.CodexClient(token_path="~/.my-tokens/auth.json")

# Custom login handler (for web apps, TUIs, etc.)
def my_handler(url: str) -> str:
    """Receive auth URL, return the callback URL after user authenticates."""
    show_qr_code(url)
    return wait_for_user_paste()

client = codex_py.CodexClient(login_handler=my_handler)

# Configure retries and timeout
client = codex_py.CodexClient(max_retries=3, timeout=60.0)
```

The constructor handles auth internally — gets cached token or triggers login.
Builds headers (Bearer + `ChatGPT-Account-ID` from JWT). The client is
stateless per-request — no persistent connection (WebSocket would change this later).

## Authentication

Three tiers of login control:

| Method | Who controls UX | Server needed |
|--------|----------------|---------------|
| `login()` | Library (opens browser + local server) | Yes |
| `login(no_browser=True)` | Library (prints URL + local server) | Yes |
| `login(headless=True)` | Library (prints URL, reads stdin) | No |
| `start_login()` / `finish_login()` | The app entirely | No |

### Automatic (default)

```python
# Opens browser, starts local server on :1455, catches callback
codex_py.login()

# Prints URL, but still runs local server to catch callback
codex_py.login(no_browser=True)

# Prints URL, user pastes redirect URL back into stdin
codex_py.login(headless=True)
```

### Manual two-step (for apps that control the UX)

```python
# Step 1: Get the auth URL and PKCE state
auth = codex_py.start_login()
auth.url       # OAuth URL to present to the user

# ... app shows URL in its own UI, user authenticates ...

# Step 2: Complete with the callback URL
tokens = codex_py.finish_login(
    auth,
    callback_url="http://localhost:1455/auth/callback?code=...&state=...",
)
```

### Login handler (for CodexClient)

```python
# The client calls your handler when login is needed
def my_handler(url: str) -> str:
    """Receives the OAuth URL, returns the callback URL after auth."""
    ...

client = codex_py.CodexClient(login_handler=my_handler)
```

## Core Methods

### `client.models.list()`

```python
models = client.models.list()
# Returns: list[Model]

models[0].slug              # "gpt-5.3-codex"
models[0].display_name      # "gpt-5.3-codex"
models[0].context_window    # 272000
models[0].reasoning_levels  # ["low", "medium", "high"]
models[0].input_modalities  # ["text", "image"]

# Bypass the 5-minute cache
models = client.models.list(force_refresh=True)
```

Returns a list of `Model` dataclasses. Cached in memory with a 5-minute TTL
(matching CLI behavior).

### `client.responses.create()`

The main method. Three `@overload` signatures following the OpenAI SDK pattern:

```python
# Overload 1: stream=False (default) -> Response
@overload
def create(
    self,
    *,
    model: str,
    instructions: str,
    input: str | list[InputItem],
    stream: Literal[False] = False,
    ...
) -> Response: ...

# Overload 2: stream=True -> ResponseStream
@overload
def create(
    self,
    *,
    model: str,
    instructions: str,
    input: str | list[InputItem],
    stream: Literal[True],
    ...
) -> ResponseStream: ...

# Overload 3: stream=bool -> union
@overload
def create(
    self,
    *,
    stream: bool,
    ...
) -> Response | ResponseStream: ...
```

#### Usage examples

```python
# Simple text
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are a helpful assistant.",
    input="What is 2+2?",
)
print(response.output_text)

# Structured input (multi-turn)
response = client.responses.create(
    model="gpt-5.1-codex",
    instructions="You are a coding assistant.",
    input=[
        InputMessage(role="user", content="Write a fibonacci function"),
        InputMessage(role="assistant", content="def fib(n): ..."),
        InputMessage(role="user", content="Now add memoization"),
    ],
)

# Dict-based input also works
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input=[{"role": "user", "content": "Hello"}],
)

# With reasoning
response = client.responses.create(
    model="gpt-5.1-codex",
    instructions="Think carefully.",
    input="Prove that sqrt(2) is irrational.",
    reasoning=Reasoning(effort="high", summary="detailed"),
)
print(response.reasoning_summary)

# With images
response = client.responses.create(
    model="gpt-5.3-codex",
    instructions="Describe what you see.",
    input=[InputMessage(
        role="user",
        content=[
            InputText(text="What's in this image?"),
            InputImage(image_url="data:image/png;base64,..."),
        ],
    )],
)

# With tools (function calling)
response = client.responses.create(
    model="gpt-5.1-codex",
    instructions="Use tools when needed.",
    input="What's the weather in Tokyo?",
    tools=[FunctionTool(
        name="get_weather",
        description="Get weather for a city",
        parameters={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )],
)

# Tool call roundtrip
if response.tool_calls:
    call = response.tool_calls[0]
    result = execute_my_function(call.name, call.arguments)
    # Filter out reasoning items — they have server-side IDs
    # that can't be referenced with store=false
    output_items = [
        item for item in response.output
        if not isinstance(item, ResponseReasoningItem)
    ]
    response = client.responses.create(
        model="gpt-5.1-codex",
        instructions="Use tools when needed.",
        input=[
            InputMessage(role="user", content="What's the weather in Tokyo?"),
            *output_items,
            FunctionCallOutput(call_id=call.call_id, output=result),
        ],
    )
```

### Parameters

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `model` | `str` | Yes | — | Model slug |
| `instructions` | `str` | Yes | — | System prompt |
| `input` | `str \| list[InputItem]` | Yes | — | String auto-wrapped to `[InputMessage(role="user", ...)]` |
| `tools` | `list[Tool]` | No | `None` | Function/tool definitions |
| `tool_choice` | `Literal["auto", "none", "required"]` | No | `None` | |
| `parallel_tool_calls` | `bool` | No | `None` | Per-model default if not set |
| `reasoning` | `Reasoning` | No | `None` | `Reasoning(effort=..., summary=...)` |
| `text` | `TextConfig` | No | `None` | `TextConfig(verbosity="medium")` |
| `stream` | `bool` | No | `False` | Controls return type via overloads |
| `service_tier` | `Literal["auto", "flex", "priority"]` | No | `None` | |
| `include` | `list[str]` | No | `None` | e.g. `["reasoning.encrypted_content"]` |
| `previous_response_id` | `str` | No | `None` | For multi-turn continuations |
| `timeout` | `float` | No | `None` | Request timeout in seconds |

`store=False` and `stream=True` are always sent to the API internally. The `stream`
parameter controls whether the user gets a `ResponseStream` or a collected `Response`.
When `stream=False`, we still stream from the API but collect and return the final result.

### Streaming

```python
stream = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="You are helpful.",
    input="Write a poem about Python.",
    stream=True,
)

for event in stream:
    match event.type:
        case "response.output_text.delta":
            print(event.delta, end="", flush=True)
        case "response.reasoning_summary_text.delta":
            pass
        case "response.output_item.done":
            pass
        case "response.completed":
            print(f"\nTokens: {event.response.usage}")
        case "response.failed":
            print(f"Error: {event.response.error}")

# Or consume the stream and get the final response
stream = client.responses.create(..., stream=True)
response = stream.get_final_response()
print(response.output_text)
```

### `ResponseStream`

```python
class ResponseStream:
    """Iterable of ResponseStreamEvent with helper methods."""

    def __iter__(self) -> Iterator[ResponseStreamEvent]: ...
    def get_final_response(self) -> Response: ...
    def close(self) -> None: ...
```

Iterating a consumed stream replays cached events. `get_final_response()` consumes
the stream if not already consumed, raises `StreamError` if no terminal event.

### Stream event types

Same SSE event names as OpenAI — users can transfer knowledge from the OpenAI SDK.

| Event type | Key fields | Description |
|---|---|---|
| `response.created` | `response: Response` | Response object created |
| `response.in_progress` | `response: Response` | Processing started |
| `response.completed` | `response: Response` | Done, includes usage |
| `response.failed` | `response: Response` | Failed, includes error |
| `response.incomplete` | `response: Response` | Truncated |
| `response.output_item.added` | `item: OutputItem, output_index` | New output item started |
| `response.output_item.done` | `item: OutputItem, output_index` | Output item completed |
| `response.output_text.delta` | `delta: str, output_index, content_index` | Text chunk |
| `response.output_text.done` | `text: str, output_index, content_index` | Full text of content part |
| `response.function_call_arguments.delta` | `delta: str, output_index` | Tool call args chunk |
| `response.function_call_arguments.done` | `arguments: str, output_index` | Full tool call args |
| `response.reasoning_summary_text.delta` | `delta: str, output_index` | Reasoning chunk |
| `response.reasoning_summary_text.done` | `text: str, output_index` | Full reasoning summary |

## Data Types

All types use `dataclass(slots=True)` for performance.
Dict-based input is also accepted wherever typed objects are expected
(e.g. `{"role": "user", "content": "..."}` works alongside `InputMessage(...)`).

### Input types

```python
InputItem = Union[
    InputMessage,
    ResponseOutputMessage,
    FunctionCallOutput,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
]

@dataclass(slots=True)
class InputMessage:
    role: Literal["user", "assistant", "system", "developer"]
    content: str | list[ContentPart]
    type: Literal["message"] = "message"

@dataclass(slots=True)
class InputText:
    text: str
    type: Literal["input_text"] = "input_text"

@dataclass(slots=True)
class InputImage:
    image_url: str                   # data:image/png;base64,... or URL
    detail: Literal["auto", "low", "high"] = "auto"
    type: Literal["input_image"] = "input_image"

ContentPart = Union[InputText, InputImage]

@dataclass(slots=True)
class FunctionCallOutput:
    call_id: str
    output: str
    type: Literal["function_call_output"] = "function_call_output"
```

### Output types

```python
OutputItem = Union[
    ResponseOutputMessage,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
]

@dataclass(slots=True)
class ResponseOutputMessage:
    id: str
    content: list[OutputContent]
    role: Literal["assistant"] = "assistant"
    status: str | None = None
    type: Literal["message"] = "message"

@dataclass(slots=True)
class OutputText:
    text: str
    type: Literal["output_text"] = "output_text"

OutputContent = Union[OutputText]    # extensible for future content types

@dataclass(slots=True)
class ResponseFunctionToolCall:
    call_id: str
    name: str
    arguments: str                    # raw JSON string
    id: str | None = None
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    type: Literal["function_call"] = "function_call"

@dataclass(slots=True)
class ResponseReasoningItem:
    id: str
    summary: list[ReasoningSummary]
    encrypted_content: str | None = None
    type: Literal["reasoning"] = "reasoning"

@dataclass(slots=True)
class ReasoningSummary:
    text: str
    type: Literal["summary_text"] = "summary_text"
```

### Response

```python
@dataclass(slots=True)
class Response:
    id: str
    model: str
    output: list[OutputItem]
    status: Literal["completed", "failed", "incomplete"] | None = None
    usage: Usage | None = None
    error: ResponseError | None = None

    @property
    def output_text(self) -> str:
        """Join all output_text content blocks from output messages."""

    @property
    def reasoning_summary(self) -> str | None:
        """Join all reasoning summary texts."""

    @property
    def tool_calls(self) -> list[ResponseFunctionToolCall]:
        """Extract all function tool calls from output."""

@dataclass(slots=True)
class ResponseError:
    code: str
    message: str

@dataclass(slots=True)
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
```

### Tool definitions

```python
@dataclass(slots=True)
class FunctionTool:
    name: str
    description: str
    parameters: dict[str, Any]       # must include "additionalProperties": False
    strict: bool = True
    type: Literal["function"] = "function"

Tool = Union[FunctionTool]           # extensible for web_search, etc.
```

### Config types

```python
@dataclass(slots=True)
class Reasoning:
    effort: Literal["low", "medium", "high"] | None = None
    summary: Literal["auto", "concise", "detailed", "none"] | None = None

@dataclass(slots=True)
class TextConfig:
    verbosity: Literal["low", "medium", "high"] | None = None
```

### Model

```python
@dataclass(slots=True)
class Model:
    slug: str
    display_name: str
    context_window: int | None = None
    reasoning_levels: list[str] = field(default_factory=list)
    input_modalities: list[str] = field(default_factory=list)
    supports_parallel_tool_calls: bool = False
    priority: int = 0
```

## Error Handling

```python
from codex_py import CodexError, AuthError, RateLimitError, ContextWindowError

try:
    response = client.responses.create(...)
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except ContextWindowError:
    print("Input too long for model's context window")
except AuthError:
    print("Token expired and refresh failed")
    client.login()
except CodexError as e:
    print(f"API error: {e.code} — {e.message}")
```

### Exception hierarchy

Follows the OpenAI SDK pattern:

```
CodexError (base)
├── APIError
│   ├── code: str | None
│   ├── message: str
│   ├── status_code: int
│   ├── body: object
│   │
│   ├── AuthError              — 401/403, token expired, refresh failed
│   ├── RateLimitError         — 429, has retry_after: float | None
│   ├── InvalidRequestError    — 400, bad parameters
│   │   └── ContextWindowError — context_length_exceeded
│   ├── QuotaExceededError     — subscription quota exhausted
│   └── ServerError            — 5xx, overloaded
│
├── APIConnectionError         — network failure, no response
│   └── APITimeoutError        — request timed out
│
└── StreamError                — stream closed unexpectedly, incomplete response
```

### Built-in retry

`ServerError` and `RateLimitError` are retried automatically (configurable).
The client parses "try again in X.XXXs" from error messages (same as the CLI).
Default: 2 retries with exponential backoff.

```python
client = codex_py.CodexClient(max_retries=3)   # default: 2
```

## Token Lifecycle

The client handles token refresh transparently at construction time.
If the cached token is expired, the client tries to refresh before falling
back to a full login flow.

```python
client = codex_py.CodexClient()
# Token refreshed automatically at construction if needed
# If refresh token is also expired, triggers login flow
# User can explicitly re-login:
client.login()

# Access the current token and account ID
client.token        # str
client.account_id   # str | None
```

## Future: WebSocket Transport

Opt-in persistent connection for multi-turn performance:

```python
async with client.connect(model="gpt-5.1-codex") as session:
    r1 = await session.send("Hello")
    r2 = await session.send("Follow up")  # uses previous_response_id, no full resend
    # Connection persists up to 60 minutes
```

The sync `client.responses.create()` remains the primary interface.
WebSocket is async-only, opt-in for users who need multi-turn performance.

## Current Project State

### Source files

```
src/codex_py/
├── __init__.py      — public re-exports: CodexClient, all types, all errors,
│                      login functions, API helpers
├── _version.py      — __version__ = "0.1.0"
├── _pkce.py         — PKCE verifier + SHA-256 challenge generation
├── _config.py       — OAuth constants, TokenData dataclass, load/save ~/.codex/auth.json
│                      Constants: CLIENT_ID, AUTH_ENDPOINT, TOKEN_ENDPOINT, REDIRECT_URI,
│                      SCOPES, AUDIENCE, CODEX_BASE_URL, CODEX_CLIENT_VERSION, DEFAULT_TOKEN_PATH
├── _server.py       — Local HTTP server on :1455 to catch OAuth callback
│                      Uses threading.Event for reliable callback detection
├── _auth.py         — login() (interactive/headless/no_browser), refresh(), get_token(),
│                      start_login(), finish_login(), PendingLogin
├── _api.py          — _decode_jwt_payload(), get_account_id(), build_headers(), list_models()
├── _types.py        — All typed dataclasses: Response, OutputItem/InputItem unions,
│                      stream events, FunctionTool, Reasoning, TextConfig, Model, Usage
├── _errors.py       — Exception hierarchy: CodexError, APIError, AuthError,
│                      RateLimitError, InvalidRequestError, ContextWindowError, etc.
├── _stream.py       — SSE parser (iter_sse_lines), event parsing (_parse_sse_event),
│                      response parsing (_parse_response), ResponseStream class
├── _responses.py    — Responses resource with create() (@overload for stream typing),
│                      input serialization, retry logic for 429/5xx
├── _models.py       — Models resource with list(), 5-minute TTL cache, force_refresh
└── _client.py       — CodexClient class with .responses and .models sub-resources,
                       auth lifecycle, login_handler support, max_retries, timeout
```

### Test files

```
tests/
├── test_version.py       — (1) version check
├── test_pkce.py          — (4) verifier length, URL-safety, randomness, challenge
├── test_config.py        — (8) TokenData expiry, save/load roundtrip, edge cases
├── test_auth.py          — (9) URL building, code extraction, cached token,
│                           start_login/finish_login
├── test_api.py           — (7) JWT decoding, account ID extraction, header building
├── test_types.py         — (11) Response properties, defaults, output_text, tool_calls
├── test_errors.py        — (17) hierarchy, raise_for_status, retry_after parsing
├── test_stream.py        — (25) SSE parsing, all event types, ResponseStream
├── test_responses.py     — (12) input serialization, Reasoning/TextConfig/Tool serialization
├── test_models.py        — (4) model parsing, cache staleness
├── test_client_unit.py   — (3) CodexClient with cached tokens, login_handler
├── test_live.py          — [pytest -m live] (7) original API tests: token, refresh,
│                           headers, models, raw responses endpoint
├── test_client_live.py   — [pytest -m live] (15) CodexClient tests: simple response,
│                           usage, streaming, text deltas, multi-turn, dict input,
│                           reasoning, model fields, force_refresh, tool call, roundtrip
└── test_interactive.py   — [pytest -m interactive -s] (5) real OAuth login flows:
                            auto, no_browser, headless, start/finish, login_handler
```

### Commands

- `uv run pytest` — unit tests (100, live/interactive excluded by default)
- `uv run pytest -m live` — live API tests (22, require ~/.codex/auth.json)
- `uv run pytest -m interactive -s -k <test>` — interactive login tests (5, one at a time)
- `uv run mypy src/codex_py/ tests/ --strict` — type checking
- `uv run ruff check` — linting
- `uv sync --all-extras` — install all deps

## Out of Scope

- `openai.OpenAI()` wrapper — the APIs are too different
- Compaction / context management — application logic, not client logic
- Local tool execution — the client reports tool calls, the user executes them
- Realtime audio WebSocket — different protocol, different use case
- App-server IPC — VS Code extension concern
