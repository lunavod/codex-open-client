# Authentication

`codex-open-client` uses OAuth 2.0 with PKCE to authenticate against OpenAI's auth server. Tokens are cached at `~/.codex/auth.json` (shared with the official Codex CLI).

## Authentication Modes

### Default — Browser + Local Server

Opens your browser and starts a local server on `localhost:1455` to catch the callback:

```python
client = codex_open_client.CodexClient()
```

Best for local development on a machine with a browser.

### No Browser — Print URL + Local Server

Prints the URL instead of opening a browser, but still uses the local callback server:

```python
client = codex_open_client.CodexClient(no_browser=True)
```

Useful when running over SSH with port forwarding, or when `webbrowser.open()` doesn't work.

### Headless — No Server

Prints the URL and prompts the user to paste the callback URL back. No local server needed:

```python
client = codex_open_client.CodexClient(headless=True)
```

Works anywhere — Docker containers, remote servers, CI environments.

### Custom Login Handler

Full control over the authentication UX. Your handler receives the OAuth URL and returns the callback URL:

```python
def my_handler(url: str) -> str:
    # Show URL to user however you want
    print(f"Please visit: {url}")
    # Get the callback URL back however you want
    return input("Paste redirect URL: ").strip()

client = codex_open_client.CodexClient(login_handler=my_handler)
```

This is the best option for integrating into a larger application — you control how the URL is presented (GUI dialog, Slack message, email, etc.) and how the callback is collected.

## Token Lifecycle

1. **Cache check** — loads `~/.codex/auth.json`, uses the token if not expired
2. **Refresh** — if expired but a refresh token exists, exchanges it for a new access token
3. **Login** — if no valid token and no refresh token, triggers one of the login modes above

All of this happens automatically in the `CodexClient` constructor. You never need to manage tokens manually.

## Custom Token Path

```python
client = codex_open_client.CodexClient(token_path="~/.myapp/tokens.json")
```

## Two-Step Login (Advanced)

For frameworks where you can't block on user input, use the two-step flow:

```python
# Step 1: Get the OAuth URL
auth = codex_open_client.start_login()
print(auth.url)  # Present this to the user

# ... user authenticates in their browser ...
# ... collect the callback URL somehow ...

# Step 2: Exchange the callback for tokens
tokens = codex_open_client.finish_login(auth, callback_url=callback_url)
print(tokens.access_token)
```

## Standalone Functions

If you don't need a full client, you can use the auth functions directly:

```python
# Get a token (handles cache + refresh + login)
token = codex_open_client.get_token()

# Build headers for manual requests
headers = codex_open_client.build_headers(token)

# Extract account ID from a token
account_id = codex_open_client.get_account_id(token)
```
