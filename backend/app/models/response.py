from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class ChatCompletionMessageDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[ChatCompletionMessageDelta] = None
    delta: Optional[ChatCompletionMessageDelta] = None
    finish_reason: Optional[str] = None
    logprobs: Optional[Any] = None


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion", "chat.completion.chunk"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[UsageInfo] = None
    system_fingerprint: Optional[str] = None

    # RoutingBrain metadata (injected into non-streaming responses)
    x_routing_decision: Optional[Dict[str, Any]] = None
