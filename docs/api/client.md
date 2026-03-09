# CodexClient

The main entry point for the Codex API.

::: codex_py.CodexClient
    options:
      members:
        - __init__
        - login
        - token
        - account_id

## Responses

::: codex_py._responses.Responses
    options:
      members:
        - create

## ResponseStream

::: codex_py._stream.ResponseStream
    options:
      members:
        - __iter__
        - get_final_response
        - close
        - __enter__
        - __exit__

## Models

::: codex_py._models.Models
    options:
      members:
        - list

## Authentication Functions

### login

::: codex_py.login

### get_token

::: codex_py.get_token

### refresh

::: codex_py.refresh

### start_login

::: codex_py.start_login

### finish_login

::: codex_py.finish_login

### PendingLogin

::: codex_py.PendingLogin

## Helper Functions

### build_headers

::: codex_py.build_headers

### get_account_id

::: codex_py.get_account_id
