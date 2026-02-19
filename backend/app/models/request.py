from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class MessageContentPart(BaseModel):
    type: Literal["text", "image_url"]
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, List[MessageContentPart], None] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        if isinstance(self.content, list):
            return " ".join(p.text or "" for p in self.content if p.type == "text")
        return ""


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    user: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None

    # RoutingBrain extension fields (passed via extra headers, injected here by middleware)
    x_department: Optional[str] = Field(default=None, alias="x_department")
    x_budget_tier: Optional[str] = Field(default=None, alias="x_budget_tier")
    x_request_id: Optional[str] = Field(default=None, alias="x_request_id")
    x_user_id: Optional[str] = Field(default=None, alias="x_user_id")
    x_tenant_id: Optional[str] = Field(default=None, alias="x_tenant_id")

    model_config = {"populate_by_name": True}
