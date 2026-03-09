# Models

List available Codex models and their capabilities.

## Listing Models

```python
models = client.models.list()

for m in models:
    print(f"{m.slug:30} context={m.context_window}")
```

## Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | Model identifier (e.g. `"gpt-5.1-codex-mini"`) |
| `display_name` | `str` | Human-readable name |
| `context_window` | `int \| None` | Maximum context length in tokens |
| `reasoning_levels` | `list[str]` | Supported reasoning effort levels |
| `input_modalities` | `list[str]` | Supported input types (e.g. `["text", "image"]`) |
| `supports_parallel_tool_calls` | `bool` | Whether parallel tool calls are supported |
| `priority` | `int` | Display priority |

## Caching

Model results are cached for 5 minutes to avoid redundant API calls. Force a refresh:

```python
# Uses cache if available
models = client.models.list()

# Bypasses cache
models = client.models.list(force_refresh=True)
```

## Finding a Specific Model

```python
models = client.models.list()

# Find by slug
mini = next((m for m in models if m.slug == "gpt-5.1-codex-mini"), None)
if mini:
    print(f"Context window: {mini.context_window}")
    print(f"Reasoning levels: {mini.reasoning_levels}")
```
