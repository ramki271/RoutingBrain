import time
import uuid
from typing import AsyncGenerator

import httpx

from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.models.request import ChatCompletionRequest
from app.models.response import (
    ChatCompletionChoice,
    ChatCompletionMessageDelta,
    ChatCompletionResponse,
    UsageInfo,
)
from app.providers.base import BaseProvider

logger = get_logger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama local provider — uses Ollama's OpenAI-compatible API."""

    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    def _build_messages(self, request: ChatCompletionRequest) -> list:
        return [
            {"role": msg.role, "content": msg.text_content()}
            for msg in request.messages
        ]

    async def chat_completion(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        try:
            payload = {
                "model": model,
                "messages": self._build_messages(request),
                "stream": False,
            }
            if request.temperature is not None:
                payload["options"] = {"temperature": request.temperature}

            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content", "")
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                object="chat.completion",
                created=int(time.time()),
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessageDelta(
                            role="assistant", content=content
                        ),
                        finish_reason="stop",
                    )
                ],
            )
        except httpx.HTTPStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.response.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest, model: str
    ) -> AsyncGenerator[str, None]:
        import orjson

        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

        try:
            payload = {
                "model": model,
                "messages": self._build_messages(request),
                "stream": True,
            }

            async with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = orjson.loads(line)
                    except Exception:
                        continue

                    content = data.get("message", {}).get("content", "")
                    done = data.get("done", False)

                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content} if content else {},
                                "finish_reason": "stop" if done else None,
                            }
                        ],
                    }
                    yield self._sse_line(orjson.dumps(chunk).decode())
                    if done:
                        break

            yield self._sse_done()

        except httpx.HTTPStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.response.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def health_check(self) -> bool:
        try:
            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
