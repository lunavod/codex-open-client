# codex-py — Research & Findings

## What is this?

A Python client for OpenAI Codex, allowing ChatGPT Plus/Pro subscribers to use their subscription for API access without separate API credits.

## Architecture Overview

Codex OAuth tokens do **not** work with `api.openai.com`. The subscription-authenticated API is a completely separate backend:

| Concern | API Key (standard) | Codex OAuth (subscription) |
|---------|--------------------|-----------------------------|
| Base URL | `https://api.openai.com/v1` | `https://chatgpt.com/backend-api/codex` |
| Auth | `Authorization: Bearer <api_key>` | Bearer token + `ChatGPT-Account-ID` header |
| Completions | `/chat/completions` or `/responses` | `/responses` only |
| Models | `GET /models` | `GET /models?client_version=X` |
| Format | Standard OpenAI API | Responses API with required fields |

## OAuth Flow

Codex CLI uses **OAuth 2.0 PKCE** (Proof Key for Code Exchange).

### Parameters

| Parameter | Value |
|-----------|-------|
| Client ID | `app_EMoamEEZ73f0CkXaXp7hrann` |
| Authorization endpoint | `https://auth.openai.com/oauth/authorize` |
| Token endpoint | `https://auth.openai.com/oauth/token` |
| Redirect URI | `http://localhost:1455/auth/callback` |
| Scopes | `openid profile email offline_access` |
| Audience | `https://api.openai.com/v1` |
| Token storage | `~/.codex/auth.json` |

### Scopes

Only identity scopes work in the OAuth request. API-level scopes (`model.request`, `api.model.read`, `api.responses.write`) are **rejected** by the auth server — requesting them returns "The requested scope is invalid." These permissions are granted implicitly based on the client ID and audience.

### Flow

1. Generate a PKCE code verifier (128 chars, URL-safe) + SHA-256 challenge
2. Open browser to authorization endpoint with challenge
3. Listen on `localhost:1455` for the callback (or headless: user pastes redirect URL)
4. Exchange auth code + verifier for access/refresh tokens at the token endpoint
5. Store tokens in `~/.codex/auth.json`
6. Auto-refresh when token expires (refresh token enables long-lived sessions)

## Codex API

### Required Headers

| Header | Value | Source |
|--------|-------|--------|
| `Authorization` | `Bearer <access_token>` | Standard OAuth |
| `ChatGPT-Account-ID` | Account ID from JWT | Decoded from `https://api.openai.com/auth` claim |
| `OpenAI-Beta` | `responses=experimental` | Required beta header |
| `originator` | `codex_cli_rs` | Client identifier |

The `ChatGPT-Account-ID` is extracted by decoding the JWT access token's payload (base64, no verification needed). The payload contains a `https://api.openai.com/auth` claim with a `chatgpt_account_id` field.

### Models Endpoint

```
GET https://chatgpt.com/backend-api/codex/models?client_version=0.99.0
Authorization: Bearer <token>
ChatGPT-Account-ID: <account_id>
```

Returns rich model metadata (unlike the standard `/v1/models` which only has id/created/owned_by):

```json
{
  "models": [
    {
      "slug": "gpt-5.3-codex",
      "display_name": "gpt-5.3-codex",
      "context_window": 272000,
      "default_reasoning_level": "medium",
      "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}],
      "input_modalities": ["text", "image"],
      "supports_parallel_tool_calls": true,
      "base_instructions": "...",
      "priority": 0,
      "visibility": "list",
      "supported_in_api": true
    }
  ]
}
```

The CLI caches this to `~/.codex/models_cache.json` with a 5-minute TTL and ETag.

### Responses Endpoint

```
POST https://chatgpt.com/backend-api/codex/responses
Authorization: Bearer <token>
ChatGPT-Account-ID: <account_id>
OpenAI-Beta: responses=experimental
originator: codex_cli_rs
```

**Required body fields** (will get 400 without these):
- `model` — model slug (e.g., `gpt-5.1-codex-mini`)
- `input` — **must be a list** of message objects, not a string
- `instructions` — system instructions (required, not optional)
- `store: false` — required for stateless mode
- `stream: true` — always stream

Response is SSE with events like `response.created`, `response.in_progress`, `response.output_item.added`, `response.completed`.

### WebSocket Transport

The Codex CLI can also use WebSocket instead of REST+SSE for the responses endpoint:

```
wss://chatgpt.com/backend-api/codex/responses
```

Same event model, but the connection persists across turns. Benefits:
- No full-context re-send each turn — only incremental input + `previous_response_id`
- ~15-50% faster depending on task complexity
- 60-minute connection lifetime with auto-reconnect

Currently behind feature flags (`ResponsesWebsockets`, `ResponsesWebsocketsV2`) and still under development. Falls back to REST+SSE if WebSocket handshake fails (HTTP 426). The v2 protocol uses beta header `OpenAI-Beta: responses_websockets=2026-02-06`.

There are also separate WebSocket systems for realtime audio and local app-server IPC (JSON-RPC), but those aren't relevant to this library.

## Existing Ecosystem

### Node.js

- **opencode-openai-codex-auth** — Most mature community extraction. Intercepts fetch to rewrite URLs from `api.openai.com` to `chatgpt.com/backend-api/codex`, injects required headers, transforms request bodies.
  - Repo: [numman-ali/opencode-openai-codex-auth](https://github.com/numman-ali/opencode-openai-codex-auth)
  - Supports 22+ model/reasoning-level permutations
- **opencode-openai-device-auth** — Device Code flow variant for headless/SSH
  - Repo: [tumf/opencode-openai-device-auth](https://github.com/tumf/opencode-openai-device-auth)

### Go

- **OpenClaw** — AI coding assistant with built-in Codex OAuth.
  - Repo: [openclaw/openclaw](https://github.com/openclaw/openclaw)
  - Hit scope issues early on (missing `model.request`, `api.responses.write`)
  - Also hit 401 when mistakenly routing to `api.openai.com` instead of `chatgpt.com/backend-api/codex`

### Python

- No standalone Python library exists that implements the full Codex API flow
- **oh-my-codex** — delegates to the CLI binary, doesn't implement OAuth
- Open feature request: [openai/codex#2772](https://github.com/openai/codex/issues/2772)

## Risks & Considerations

- OpenAI could change the OAuth flow, client ID, endpoints, or required headers at any time
- Third-party use of the Codex client ID is a gray area (OpenClaw got informal confirmation)
- The `chatgpt.com/backend-api/codex` endpoint is not publicly documented
- Rate limits and ToS around subscription-based API access are unclear
- The `openai.OpenAI()` SDK wrapper approach doesn't work cleanly — the Codex backend requires different body fields and headers than the standard API

## Key Source Files (Codex CLI)

| File | What it tells us |
|------|-----------------|
| `codex-rs/core/src/model_provider_info.rs` | Base URL routing (chatgpt.com vs api.openai.com) |
| `codex-rs/codex-api/src/auth.rs` | Auth headers (Bearer + ChatGPT-Account-ID) |
| `codex-rs/codex-api/src/endpoint/responses.rs` | REST responses endpoint |
| `codex-rs/codex-api/src/endpoint/responses_websocket.rs` | WebSocket responses transport |
| `codex-rs/codex-api/src/endpoint/models.rs` | Models listing endpoint |
| `codex-rs/protocol/src/openai_models.rs` | Model metadata schema |
| `codex-rs/core/src/features.rs` | Feature flags (WebSocket modes) |
| `codex-rs/core/models.json` | Bundled fallback model catalog |

## References

- [OpenAI Codex CLI](https://github.com/openai/codex)
- [OpenAI Codex Authentication Docs](https://developers.openai.com/codex/auth/)
- [WebSocket Mode for Responses API](https://developers.openai.com/api/docs/guides/websocket-mode/)
- [Best practice for ClientID (OpenAI Forum)](https://community.openai.com/t/best-practice-for-clientid-when-using-codex-oauth/1371778)
- [WebSockets for Responses API (OpenAI Forum)](https://community.openai.com/t/websockets-for-responses-api/1374906)
