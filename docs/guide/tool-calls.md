# Tool Calls

The Codex API supports function calling — the model can invoke tools you define, and you handle the execution.

## Defining Tools

```python
import json
import codex_py

client = codex_py.CodexClient()

weather_tool = codex_py.FunctionTool(
    name="get_weather",
    description="Get the current weather for a city.",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
        "additionalProperties": False,
    },
)
```

!!! warning "additionalProperties is required"
    The Codex API requires `"additionalProperties": False` in the tool's parameters schema.
    Requests without it will return a 400 error.

## Making a Tool Call Request

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Use tools when helpful.",
    input="What's the weather in Tokyo?",
    tools=[weather_tool],
)

# Check if the model wants to call a tool
for call in response.tool_calls:
    print(f"Function: {call.name}")
    print(f"Arguments: {call.arguments}")  # raw JSON string
    args = json.loads(call.arguments)
    print(f"City: {args['city']}")
```

## Tool Call Roundtrip

After executing the tool, feed the result back:

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Use tools when helpful.",
    input="What's the weather in Tokyo?",
    tools=[weather_tool],
)

if response.tool_calls:
    # Execute the tool (your logic)
    result = get_weather(json.loads(response.tool_calls[0].arguments)["city"])

    # Feed the result back — filter out reasoning items
    input_items = [
        item for item in response.output
        if not isinstance(item, codex_py.ResponseReasoningItem)
    ]
    input_items.append(
        codex_py.FunctionCallOutput(
            call_id=response.tool_calls[0].call_id,
            output=json.dumps(result),
        )
    )

    final = client.responses.create(
        model="gpt-5.1-codex-mini",
        instructions="Use tools when helpful.",
        input=input_items,
        tools=[weather_tool],
    )
    print(final.output_text)
```

!!! note "Filter reasoning items"
    When feeding `response.output` back as input, always filter out
    `ResponseReasoningItem` objects. They contain server-side IDs that can't
    be referenced when `store=false` (which codex-py always sets).

## Tool Choice

Control whether the model should use tools:

```python
# Let the model decide (default)
response = client.responses.create(..., tools=[weather_tool], tool_choice="auto")

# Force the model to call a tool
response = client.responses.create(..., tools=[weather_tool], tool_choice="required")

# Prevent tool use
response = client.responses.create(..., tools=[weather_tool], tool_choice="none")
```

## Dict-Based Tools

You can also pass tools as raw dicts:

```python
response = client.responses.create(
    model="gpt-5.1-codex-mini",
    instructions="Use tools.",
    input="What's the weather?",
    tools=[{
        "type": "function",
        "name": "get_weather",
        "description": "Get weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    }],
)
```
