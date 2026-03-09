# CodexClient

The main entry point for the Codex API.

::: codex_open_client.CodexClient
    options:
      members:
        - __init__
        - login
        - token
        - account_id

## Responses

::: codex_open_client._responses.Responses
    options:
      members:
        - create

## ResponseStream

::: codex_open_client._stream.ResponseStream
    options:
      members:
        - __iter__
        - get_final_response
        - close
        - __enter__
        - __exit__

## Models

::: codex_open_client._models.Models
    options:
      members:
        - list

## Authentication Functions

### login

::: codex_open_client.login

### get_token

::: codex_open_client.get_token

### refresh

::: codex_open_client.refresh

### start_login

::: codex_open_client.start_login

### finish_login

::: codex_open_client.finish_login

### PendingLogin

::: codex_open_client.PendingLogin

## Helper Functions

### build_headers

::: codex_open_client.build_headers

### get_account_id

::: codex_open_client.get_account_id
