# codex-py

Python client for OpenAI Codex — use your ChatGPT Plus/Pro subscription for API access.

## Installation

```bash
pip install codex-py
```

## Usage

```python
import codex_py

# Get an access token (handles login, caching, and refresh)
token = codex_py.get_token()

# List available models
models = codex_py.list_models()
for m in models:
    print(m["slug"])
```

## License

MIT
