from abc import ABC, abstractmethod
from typing import AsyncGenerator, Union

from app.models.request import ChatCompletionRequest
from app.models.response import ChatCompletionResponse


class BaseProvider(ABC):
    """Abstract base class for all LLM provider adapters."""

    provider_name: str = ""

    @abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        """Non-streaming chat completion."""
        ...

    @abstractmethod
    async def chat_completion_stream(
        self, request: ChatCompletionRequest, model: str
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion. Yields SSE-formatted strings."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Returns True if the provider is reachable."""
        ...

    def _sse_line(self, data: str) -> str:
        return f"data: {data}\n\n"

    def _sse_done(self) -> str:
        return "data: [DONE]\n\n"
