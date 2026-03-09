# Changelog

## 0.2.1

- Added `"original"` detail level to `InputImage` (gpt-5.4+ only)
- Removed `file_id` from `InputImage` (not supported by Codex backend)
- Added image input documentation with detail levels and base64 examples

## 0.2.0

Structured output support.

- `responses.parse()` — pass a Pydantic `BaseModel` class, get a typed `ParsedResponse[T]` back
- `ResponseFormatJsonSchema` — constrain output to a JSON schema with `strict=True`
- `ResponseFormatJsonObject` — free-form JSON output mode
- `ResponseFormatText` — explicit plain text format
- `TextConfig.format` field for manual format configuration
- `ParsedResponse[T]` wrapper with `output_parsed` property
- Recursive `None`-stripping in serialization for clean API payloads
- Optional `pydantic` extra (`pip install codex-open-client[pydantic]`)
- Replaced `openai` optional dependency with `pydantic`

## 0.1.0

Initial release.

- OAuth 2.0 PKCE authentication with token caching and refresh
- Three login modes: browser, headless, custom handler
- Two-step login flow (`start_login` / `finish_login`)
- `CodexClient` with typed `responses.create()` and `models.list()`
- Streaming support via `ResponseStream` (SSE parsing, context manager)
- Function tool calls with roundtrip support
- Typed dataclasses for all API objects
- Exception hierarchy with automatic retry on 429/5xx
- Interop with Codex CLI token storage (`~/.codex/auth.json`)
