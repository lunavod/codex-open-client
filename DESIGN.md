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
```

The constructor handles auth internally — gets cached token or triggers login.
Builds headers (Bearer + `ChatGPT-Account-ID` from JWT). The client is
stateless per-request — no persistent connection (WebSocket would change this later).

## Authentication

Three tiers of login control:

| Method | Who controls UX | Server needed |
|--------|----------------|---------------|
| `login()` | Library (opens browser + local server) | Yes |
| `login(headless=True)` | Library (prints URL, reads stdin) | No |
| `start_login()` / `finish_login()` | The app entirely | No |

### Automatic (default)

```python
# Opens browser, starts local server on :1455, catches callback
codex_py.login()

# Prints URL, user pastes redirect URL back into stdin
codex_py.login(headless=True)

# Prints URL, but still runs local server to catch callback
codex_py.login(no_browser=True)
```

### Manual two-step (for apps that control the UX)

```python
# Step 1: Get the auth URL and PKCE state
auth = codex_py.start_login()
auth.url       # OAuth URL to present to the user
auth.state     # opaque object, pass to finish_login()

# ... app shows URL in its own UI, user authenticates ...

# Step 2: Complete with the callback URL
tokens = codex_py.finish_login(auth, callback_url="http://localhost:1455/auth/callback?code=...&state=...")
```

### Login handler (for CodexClient)

```python
# The client calls your handler when login is needed
client = codex_py.CodexClient(login_handler=my_handler)

# Handler signature:
def my_handler(url: str) -> str:
    """Receives the OAuth URL, returns the callback URL after auth."""
    ...
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
        },
    )],
)

if response.tool_calls:
    for call in response.tool_calls:
        print(call.name, call.arguments)
        result = execute_my_function(call.name, call.arguments)
        response = client.responses.create(
            model="gpt-5.1-codex",
            instructions="Use tools when needed.",
            input=[
                *response.output,
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
| `tools` | `list[Tool]` | No | `[]` | Function/tool definitions |
| `tool_choice` | `Literal["auto", "none", "required"]` | No | `"auto"` | |
| `parallel_tool_calls` | `bool` | No | `None` | Per-model default if not set |
| `reasoning` | `Reasoning` | No | `None` | `Reasoning(effort=..., summary=...)` |
| `text` | `TextConfig` | No | `None` | `TextConfig(verbosity="medium")` |
| `stream` | `bool` | No | `False` | Controls return type via overloads |
| `service_tier` | `Literal["auto", "flex", "priority"]` | No | `None` | |
| `include` | `list[str]` | No | `None` | e.g. `["reasoning.encrypted_content"]` |
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
    def __next__(self) -> ResponseStreamEvent: ...
    def get_final_response(self) -> Response: ...
    def until_done(self) -> Self: ...
    def close(self) -> None: ...
```

### Stream event types

We expose the same SSE event names as OpenAI, not simplified aliases.
This means users can transfer knowledge from the OpenAI SDK directly.

| Event type | Key fields | Description |
|---|---|---|
| `response.created` | `response: Response` | Response object created |
| `response.in_progress` | `response: Response` | Processing started |
| `response.completed` | `response: Response` | Done, includes usage |
| `response.failed` | `response: Response` | Failed, includes error |
| `response.incomplete` | `response: Response` | Truncated |
| `response.output_item.added` | `item: OutputItem` | New output item started |
| `response.output_item.done` | `item: OutputItem` | Output item completed |
| `response.output_text.delta` | `delta: str` | Text chunk |
| `response.output_text.done` | `text: str` | Full text of content part |
| `response.function_call_arguments.delta` | `delta: str` | Tool call args chunk |
| `response.function_call_arguments.done` | `arguments: str` | Full tool call args |
| `response.reasoning_summary_text.delta` | `delta: str` | Reasoning chunk |
| `response.reasoning_summary_text.done` | `text: str` | Full reasoning summary |

## Data Types

All types use `dataclass` with `__slots__` for performance.
Dict-based input is also accepted wherever typed objects are expected
(e.g. `{"role": "user", "content": "..."}` works alongside `InputMessage(...)`).

### Input types

```python
# Union of all valid input items
InputItem = Union[
    InputMessage,
    ResponseOutputMessage,
    FunctionCallOutput,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
]

@dataclass
class InputMessage:
    role: Literal["user", "assistant", "system", "developer"]
    content: str | list[ContentPart]
    type: Literal["message"] = "message"

@dataclass
class InputText:
    text: str
    type: Literal["input_text"] = "input_text"

@dataclass
class InputImage:
    image_url: str                   # data:image/png;base64,... or URL
    detail: Literal["auto", "low", "high"] = "auto"
    type: Literal["input_image"] = "input_image"

ContentPart = Union[InputText, InputImage]

@dataclass
class FunctionCallOutput:
    call_id: str
    output: str
    type: Literal["function_call_output"] = "function_call_output"
```

### Output types

```python
# Discriminated union of output items (by `type` field)
OutputItem = Union[
    ResponseOutputMessage,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
]

@dataclass
class ResponseOutputMessage:
    id: str
    content: list[OutputContent]
    role: Literal["assistant"] = "assistant"
    status: str | None = None
    type: Literal["message"] = "message"

@dataclass
class OutputText:
    text: str
    type: Literal["output_text"] = "output_text"

OutputContent = Union[OutputText]    # extensible for future content types

@dataclass
class ResponseFunctionToolCall:
    call_id: str
    name: str
    arguments: str                    # raw JSON string
    id: str | None = None
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    type: Literal["function_call"] = "function_call"

@dataclass
class ResponseReasoningItem:
    id: str
    summary: list[ReasoningSummary]
    encrypted_content: str | None = None
    type: Literal["reasoning"] = "reasoning"

@dataclass
class ReasoningSummary:
    text: str
    type: Literal["summary_text"] = "summary_text"
```

### Response

```python
@dataclass
class Response:
    id: str
    model: str
    status: Literal["completed", "failed", "incomplete"] | None
    output: list[OutputItem]
    usage: Usage | None
    error: ResponseError | None

    @property
    def output_text(self) -> str:
        """Join all output_text content blocks from output messages."""
        ...

    @property
    def reasoning_summary(self) -> str | None:
        """Join all reasoning summary texts."""
        ...

    @property
    def tool_calls(self) -> list[ResponseFunctionToolCall]:
        """Extract all function tool calls from output."""
        ...

@dataclass
class ResponseError:
    code: str
    message: str

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
```

### Stream events

```python
# Discriminated union of all stream events (by `type` field)
ResponseStreamEvent = Union[
    ResponseCreatedEvent,
    ResponseInProgressEvent,
    ResponseCompletedEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputTextDeltaEvent,
    ResponseOutputTextDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
]

@dataclass
class ResponseOutputTextDeltaEvent:
    delta: str
    type: Literal["response.output_text.delta"] = "response.output_text.delta"

@dataclass
class ResponseCompletedEvent:
    response: Response
    type: Literal["response.completed"] = "response.completed"

# ... etc for each event type
```

### Tool definitions

```python
@dataclass
class FunctionTool:
    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool = True
    type: Literal["function"] = "function"

Tool = Union[FunctionTool]           # extensible for web_search, etc.
```

### Config types

```python
@dataclass
class Reasoning:
    effort: Literal["low", "medium", "high"] | None = None
    summary: Literal["auto", "concise", "detailed", "none"] | None = None

@dataclass
class TextConfig:
    verbosity: Literal["low", "medium", "high"] | None = None
```

### Model

```python
@dataclass
class Model:
    slug: str
    display_name: str
    context_window: int | None
    reasoning_levels: list[str]       # e.g. ["low", "medium", "high"]
    input_modalities: list[str]       # e.g. ["text", "image"]
    supports_parallel_tool_calls: bool
    priority: int
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
│   │
│   ├── AuthError              — 401, token expired, refresh failed
│   ├── RateLimitError         — 429, has retry_after: float | None
│   ├── InvalidRequestError    — 400, bad parameters
│   ├── ContextWindowError     — context_length_exceeded
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
# Configure retry behavior
client = codex_py.CodexClient(
    max_retries=3,                   # default: 2
)
```

## Token Lifecycle

The client handles token refresh transparently. If a request gets 401, the client
tries to refresh the token once before raising `AuthError`.

```python
client = codex_py.CodexClient()
# Token refreshed automatically on every request if needed
# If refresh token is also expired, raises AuthError
# User can explicitly re-login:
client.login()
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

## Out of Scope

- `openai.OpenAI()` wrapper — the APIs are too different
- Compaction / context management — application logic, not client logic
- Local tool execution — the client reports tool calls, the user executes them
- Realtime audio WebSocket — different protocol, different use case
- App-server IPC — VS Code extension concern
