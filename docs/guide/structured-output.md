# Structured Output

Get model responses as typed Python objects instead of raw text.

## With Pydantic Models (Recommended)

The easiest way is `responses.parse()` — pass a Pydantic model class and get a parsed instance back:

```bash
pip install codex-open-client[pydantic]
```

```python
from pydantic import BaseModel
import codex_open_client

client = codex_open_client.CodexClient()

class Person(BaseModel):
    name: str
    age: int
    city: str

parsed = client.responses.parse(
    model="gpt-5.1-codex-mini",
    instructions="Extract the person info.",
    input="John Smith is 30 years old and lives in New York.",
    text_format=Person,
)

print(parsed.output_parsed)       # Person(name='John Smith', age=30, city='New York')
print(parsed.output_parsed.name)  # "John Smith"
print(parsed.output_parsed.age)   # 30
```

`parse()` automatically:

1. Converts the Pydantic model to a JSON schema (via `model_json_schema()`)
2. Sends it with `strict=True` so the model is guaranteed to match the schema
3. Parses the JSON response back into a model instance (via `model_validate_json()`)

### Nested Models

```python
class Address(BaseModel):
    city: str
    country: str

class Person(BaseModel):
    name: str
    address: Address

parsed = client.responses.parse(
    model="gpt-5.1-codex-mini",
    instructions="Extract the person info.",
    input="Alice lives in Paris, France.",
    text_format=Person,
)

print(parsed.output_parsed.address.city)     # "Paris"
print(parsed.output_parsed.address.country)  # "France"
```

### List Fields

```python
class ExtractedColors(BaseModel):
    colors: list[str]

parsed = client.responses.parse(
    model="gpt-5.1-codex-mini",
    instructions="Extract all colors mentioned.",
    input="The sky is blue and the grass is green.",
    text_format=ExtractedColors,
)

print(parsed.output_parsed.colors)  # ["blue", "green"]
```

### The ParsedResponse Object

`parse()` returns a `ParsedResponse[T]` which wraps the raw `Response`:

| Property | Type | Description |
|----------|------|-------------|
| `output_parsed` | `T` | The deserialized Pydantic model instance |
| `response` | `Response` | The underlying raw response |
| `output_text` | `str` | Raw JSON string (delegated from response) |
| `id` | `str` | Response ID |
| `status` | `str \| None` | `"completed"`, `"failed"`, or `"incomplete"` |
| `usage` | `Usage \| None` | Token counts |

### Combining with Other Parameters

`parse()` accepts all the same parameters as `create()`, plus `text_format`:

```python
parsed = client.responses.parse(
    model="gpt-5.1-codex-mini",
    instructions="Extract info.",
    input="...",
    text_format=MyModel,
    reasoning=codex_open_client.Reasoning(effort="high"),
    text=codex_open_client.TextConfig(verbosity="low"),
)
```

!!! warning "Don't mix `text_format` with `text.format`"
    If you pass `text_format`, the `text.format` field is set automatically.
    Passing both raises `TypeError`.

## With Manual JSON Schema

For more control (or without Pydantic), use `ResponseFormatJsonSchema` directly:

```python
import json

response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Extract the person info.",
    input="John Smith is 30 years old.",
    text=codex_open_client.TextConfig(
        format=codex_open_client.ResponseFormatJsonSchema(
            name="person",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
                "additionalProperties": False,
            },
            strict=True,
        ),
    ),
)

data = json.loads(response.output_text)
print(data["name"])  # "John Smith"
```

## JSON Object Mode

For free-form JSON (no schema), use `ResponseFormatJsonObject`:

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Reply with a JSON object.",
    input="List 3 colors. Respond in JSON.",
    text=codex_open_client.TextConfig(
        format=codex_open_client.ResponseFormatJsonObject(),
    ),
)

data = json.loads(response.output_text)
```

!!! note "Include 'JSON' in your prompt"
    When using `ResponseFormatJsonObject`, the API requires the word "json"
    to appear somewhere in your `input` or `instructions`. This isn't needed
    for `ResponseFormatJsonSchema` or `parse()`.

## Format Types Reference

| Type | `type` value | Use case |
|------|-------------|----------|
| `ResponseFormatText` | `"text"` | Plain text output (default) |
| `ResponseFormatJsonObject` | `"json_object"` | Free-form JSON |
| `ResponseFormatJsonSchema` | `"json_schema"` | Schema-constrained JSON |

All three can be passed to `TextConfig(format=...)`. You can also pass raw dicts if you prefer:

```python
text=codex_open_client.TextConfig(
    format={"type": "json_schema", "name": "person", "schema": {...}, "strict": True},
)
```
