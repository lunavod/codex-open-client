# Changelog

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
