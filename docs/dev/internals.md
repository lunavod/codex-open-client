# Internals & API Research

This page documents the Codex backend API as reverse-engineered from the
[official Codex CLI](https://github.com/openai/codex). It's intended for
contributors and anyone curious about how the subscription-based API differs
from the standard OpenAI API.

!!! warning "Undocumented API"
    The Codex backend at `chatgpt.com/backend-api/codex` is not publicly
    documented. Endpoints, headers, and behavior may change without notice.

## Codex vs Standard OpenAI API

Codex OAuth tokens do **not** work with `api.openai.com`. The subscription
API is a separate backend:

| | Standard API | Codex (subscription) |
|--|-------------|---------------------|
| Base URL | `api.openai.com/v1` | `chatgpt.com/backend-api/codex` |
| Auth | API key | OAuth bearer token + `ChatGPT-Account-ID` |
| Endpoints | `/chat/completions`, `/responses` | `/responses` only |
| Models | `GET /models` | `GET /models?client_version=X` |
| Billing | Pay-per-token | Included in ChatGPT Plus/Pro |

## OAuth Flow

The CLI uses **OAuth 2.0 PKCE** (Proof Key for Code Exchange):

1. Generate a PKCE code verifier (128 chars, URL-safe) + SHA-256 challenge
2. Open browser to the authorization endpoint with the challenge
3. Listen on `localhost:1455` for the callback (or headless: user pastes the redirect URL)
4. Exchange the auth code + verifier for access/refresh tokens
5. Store tokens in `~/.codex/auth.json`
6. Auto-refresh when the access token expires

### OAuth Parameters

| Parameter | Value |
|-----------|-------|
| Client ID | `app_EMoamEEZ73f0CkXaXp7hrann` |
| Auth endpoint | `https://auth.openai.com/oauth/authorize` |
| Token endpoint | `https://auth.openai.com/oauth/token` |
| Redirect URI | `http://localhost:1455/auth/callback` |
| Scopes | `openid profile email offline_access` |
| Audience | `https://api.openai.com/v1` |

### Scope Restrictions

Only identity scopes work. API-level scopes like `model.request`,
`api.model.read`, and `api.responses.write` are **rejected** by the auth
server with "The requested scope is invalid." The necessary API permissions
are granted implicitly based on the client ID and audience.

## Required Headers

Every request to the Codex backend needs these headers:

| Header | Value | Notes |
|--------|-------|-------|
| `Authorization` | `Bearer <access_token>` | Standard OAuth |
| `ChatGPT-Account-ID` | Account ID from JWT | See below |
| `OpenAI-Beta` | `responses=experimental` | Required |
| `originator` | `codex_cli_rs` | Client identifier |

The `ChatGPT-Account-ID` is extracted from the JWT access token payload
(base64-decoded, no signature verification needed). The payload contains a
`https://api.openai.com/auth` claim with a `chatgpt_account_id` field.

## Responses Endpoint

```
POST https://chatgpt.com/backend-api/codex/responses
```

### Required Body Fields

The endpoint returns `400` without these:

- `model` — model slug (e.g. `gpt-5.1-codex-mini`)
- `input` — must be a **list** of message objects, not a plain string
- `instructions` — system instructions (required, not optional like the standard API)
- `store: false` — required for stateless mode
- `stream: true` — always stream; non-streaming is not supported

### Response Format

Server-Sent Events with the standard Responses API event model:
`response.created`, `response.in_progress`, `response.output_text.delta`,
`response.completed`, etc.

### Tool Call Quirks

- Tool parameter schemas **must** include `"additionalProperties": false`
  or the request returns `400`
- When feeding `response.output` back as input for tool call roundtrips,
  **filter out reasoning items** — they have server-side IDs that can't be
  referenced with `store=false`

## Models Endpoint

```
GET https://chatgpt.com/backend-api/codex/models?client_version=0.99.0
```

Returns richer metadata than the standard `/v1/models`:

```json
{
  "models": [
    {
      "slug": "gpt-5.3-codex",
      "display_name": "gpt-5.3-codex",
      "context_window": 272000,
      "default_reasoning_level": "medium",
      "supported_reasoning_levels": [
        {"effort": "low"}, {"effort": "medium"}, {"effort": "high"}
      ],
      "input_modalities": ["text", "image"],
      "supports_parallel_tool_calls": true,
      "priority": 0
    }
  ]
}
```

## WebSocket Transport

The CLI also supports WebSocket transport for the responses endpoint:

```
wss://chatgpt.com/backend-api/codex/responses
```

Benefits over REST+SSE:

- No full-context re-send each turn — only incremental input + `previous_response_id`
- Lower latency for multi-turn conversations
- 60-minute connection lifetime with auto-reconnect

Currently behind feature flags (`ResponsesWebsockets`, `ResponsesWebsocketsV2`)
and still under development. The v2 protocol uses the beta header
`OpenAI-Beta: responses_websockets=2026-02-06`. Falls back to REST+SSE if the
WebSocket handshake fails (HTTP 426).

`codex-py` does not implement WebSocket transport yet.

## Key Source Files in the Codex CLI

For anyone reading the [Codex CLI source](https://github.com/openai/codex):

| File | What it tells you |
|------|------------------|
| `codex-rs/core/src/model_provider_info.rs` | Base URL routing |
| `codex-rs/codex-api/src/auth.rs` | Auth header construction |
| `codex-rs/codex-api/src/endpoint/responses.rs` | REST responses endpoint |
| `codex-rs/codex-api/src/endpoint/responses_websocket.rs` | WebSocket transport |
| `codex-rs/codex-api/src/endpoint/models.rs` | Models listing |
| `codex-rs/protocol/src/openai_models.rs` | Model metadata schema |

## References

- [OpenAI Codex CLI](https://github.com/openai/codex)
- [Codex Authentication Docs](https://developers.openai.com/codex/auth/)
- [WebSocket Mode for Responses API](https://developers.openai.com/api/docs/guides/websocket-mode/)
