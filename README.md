# codex-py

Python client for OpenAI Codex — use your ChatGPT Plus/Pro subscription for API access.

## Installation

```bash
pip install codex-py
```

## Usage

```python
import codex_py

client = codex_py.CodexClient()

# List available models
for m in client.models.list():
    print(m.slug)

# Make a request
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Be brief.",
    input="Hello!",
)
print(response.output_text)
```

## License

MIT
