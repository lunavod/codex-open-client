"""Typed data models for the Codex API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar, Union

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Config types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Reasoning:
    effort: Literal["low", "medium", "high"] | None = None
    summary: Literal["auto", "concise", "detailed", "none"] | None = None


@dataclass(slots=True)
class ResponseFormatText:
    """Plain text output (default)."""

    type: Literal["text"] = "text"


@dataclass(slots=True)
class ResponseFormatJsonObject:
    """Free-form JSON output."""

    type: Literal["json_object"] = "json_object"


@dataclass(slots=True)
class ResponseFormatJsonSchema:
    """Structured JSON output constrained to a specific schema."""

    name: str
    schema: dict[str, Any]
    type: Literal["json_schema"] = "json_schema"
    description: str | None = None
    strict: bool | None = None


FormatConfig = Union[ResponseFormatText, ResponseFormatJsonObject, ResponseFormatJsonSchema]


@dataclass(slots=True)
class TextConfig:
    format: FormatConfig | dict[str, Any] | None = None
    verbosity: Literal["low", "medium", "high"] | None = None


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class InputText:
    text: str
    type: Literal["input_text"] = "input_text"


@dataclass(slots=True)
class InputImage:
    image_url: str
    detail: Literal["auto", "low", "high", "original"] = "auto"
    type: Literal["input_image"] = "input_image"


ContentPart = Union[InputText, InputImage]


@dataclass(slots=True)
class InputMessage:
    role: Literal["user", "assistant", "system", "developer"]
    content: str | list[ContentPart]
    type: Literal["message"] = "message"


@dataclass(slots=True)
class FunctionCallOutput:
    call_id: str
    output: str
    type: Literal["function_call_output"] = "function_call_output"


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OutputText:
    text: str
    type: Literal["output_text"] = "output_text"


OutputContent = Union[OutputText]


@dataclass(slots=True)
class ResponseOutputMessage:
    id: str
    content: list[OutputContent]
    role: Literal["assistant"] = "assistant"
    status: str | None = None
    type: Literal["message"] = "message"


@dataclass(slots=True)
class ResponseFunctionToolCall:
    call_id: str
    name: str
    arguments: str
    id: str | None = None
    status: Literal["in_progress", "completed", "incomplete"] | None = None
    type: Literal["function_call"] = "function_call"


@dataclass(slots=True)
class ReasoningSummary:
    text: str
    type: Literal["summary_text"] = "summary_text"


@dataclass(slots=True)
class ResponseReasoningItem:
    id: str
    summary: list[ReasoningSummary]
    encrypted_content: str | None = None
    type: Literal["reasoning"] = "reasoning"


OutputItem = Union[ResponseOutputMessage, ResponseFunctionToolCall, ResponseReasoningItem]

# Forward-reference union for input items (includes output types for multi-turn)
InputItem = Union[
    InputMessage,
    ResponseOutputMessage,
    FunctionCallOutput,
    ResponseFunctionToolCall,
    ResponseReasoningItem,
]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FunctionTool:
    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool = True
    type: Literal["function"] = "function"


Tool = Union[FunctionTool]


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ResponseError:
    code: str
    message: str


@dataclass(slots=True)
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(slots=True)
class Response:
    id: str
    model: str
    output: list[OutputItem]
    status: Literal["completed", "failed", "incomplete"] | None = None
    usage: Usage | None = None
    error: ResponseError | None = None

    @property
    def output_text(self) -> str:
        """Join all output_text content blocks from output messages."""
        parts: list[str] = []
        for item in self.output:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, OutputText):
                        parts.append(content.text)
        return "".join(parts)

    @property
    def reasoning_summary(self) -> str | None:
        """Join all reasoning summary texts."""
        parts: list[str] = []
        for item in self.output:
            if isinstance(item, ResponseReasoningItem):
                for s in item.summary:
                    parts.append(s.text)
        return "\n".join(parts) if parts else None

    @property
    def tool_calls(self) -> list[ResponseFunctionToolCall]:
        """Extract all function tool calls from output."""
        return [item for item in self.output if isinstance(item, ResponseFunctionToolCall)]


@dataclass
class ParsedResponse(Generic[T]):
    """A response with the output text parsed into a structured object.

    Wraps a ``Response`` and adds an ``output_parsed`` attribute containing
    the deserialized model instance.

    Usage::

        from pydantic import BaseModel

        class Person(BaseModel):
            name: str
            age: int

        parsed = client.responses.parse(
            model="gpt-5.1-codex-mini",
            instructions="Extract the person info.",
            input="John Smith is 30 years old.",
            text_format=Person,
        )
        print(parsed.output_parsed.name)   # "John Smith"
        print(parsed.response.output_text)  # raw JSON string
    """

    response: Response
    output_parsed: T

    @property
    def id(self) -> str:
        return self.response.id

    @property
    def model(self) -> str:
        return self.response.model

    @property
    def output(self) -> list[OutputItem]:
        return self.response.output

    @property
    def status(self) -> Literal["completed", "failed", "incomplete"] | None:
        return self.response.status

    @property
    def usage(self) -> Usage | None:
        return self.response.usage

    @property
    def output_text(self) -> str:
        return self.response.output_text


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Model:
    slug: str
    display_name: str
    context_window: int | None = None
    reasoning_levels: list[str] = field(default_factory=list)
    input_modalities: list[str] = field(default_factory=list)
    supports_parallel_tool_calls: bool = False
    priority: int = 0


# ---------------------------------------------------------------------------
# Stream events
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ResponseCreatedEvent:
    response: Response
    type: Literal["response.created"] = "response.created"


@dataclass(slots=True)
class ResponseInProgressEvent:
    response: Response
    type: Literal["response.in_progress"] = "response.in_progress"


@dataclass(slots=True)
class ResponseCompletedEvent:
    response: Response
    type: Literal["response.completed"] = "response.completed"


@dataclass(slots=True)
class ResponseFailedEvent:
    response: Response
    type: Literal["response.failed"] = "response.failed"


@dataclass(slots=True)
class ResponseIncompleteEvent:
    response: Response
    type: Literal["response.incomplete"] = "response.incomplete"


@dataclass(slots=True)
class ResponseOutputItemAddedEvent:
    item: OutputItem
    output_index: int
    type: Literal["response.output_item.added"] = "response.output_item.added"


@dataclass(slots=True)
class ResponseOutputItemDoneEvent:
    item: OutputItem
    output_index: int
    type: Literal["response.output_item.done"] = "response.output_item.done"


@dataclass(slots=True)
class ResponseOutputTextDeltaEvent:
    delta: str
    content_index: int = 0
    output_index: int = 0
    type: Literal["response.output_text.delta"] = "response.output_text.delta"


@dataclass(slots=True)
class ResponseOutputTextDoneEvent:
    text: str
    content_index: int = 0
    output_index: int = 0
    type: Literal["response.output_text.done"] = "response.output_text.done"


@dataclass(slots=True)
class ResponseFunctionCallArgumentsDeltaEvent:
    delta: str
    output_index: int = 0
    type: Literal["response.function_call_arguments.delta"] = (
        "response.function_call_arguments.delta"
    )


@dataclass(slots=True)
class ResponseFunctionCallArgumentsDoneEvent:
    arguments: str
    output_index: int = 0
    type: Literal["response.function_call_arguments.done"] = (
        "response.function_call_arguments.done"
    )


@dataclass(slots=True)
class ResponseReasoningSummaryTextDeltaEvent:
    delta: str
    output_index: int = 0
    type: Literal["response.reasoning_summary_text.delta"] = (
        "response.reasoning_summary_text.delta"
    )


@dataclass(slots=True)
class ResponseReasoningSummaryTextDoneEvent:
    text: str
    output_index: int = 0
    type: Literal["response.reasoning_summary_text.done"] = (
        "response.reasoning_summary_text.done"
    )


ResponseStreamEvent = Union[
    ResponseCreatedEvent,
    ResponseInProgressEvent,
    ResponseCompletedEvent,
    ResponseFailedEvent,
    ResponseIncompleteEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputTextDeltaEvent,
    ResponseOutputTextDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
]
