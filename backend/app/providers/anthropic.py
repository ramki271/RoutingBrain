import time
import uuid
from typing import AsyncGenerator

import anthropic

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

# Map OpenAI role names to Anthropic role names
ROLE_MAP = {"user": "user", "assistant": "assistant"}


class AnthropicProvider(BaseProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _build_messages(self, request: ChatCompletionRequest):
        system_prompt = None
        messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.text_content()
            else:
                messages.append({"role": msg.role, "content": msg.text_content()})
        return system_prompt, messages

    async def chat_completion(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        system_prompt, messages = self._build_messages(request)
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens or 4096,
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature

            response = await self.client.messages.create(**kwargs)

            content = response.content[0].text if response.content else ""
            return ChatCompletionResponse(
                id=response.id,
                object="chat.completion",
                created=int(time.time()),
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessageDelta(
                            role="assistant", content=content
                        ),
                        finish_reason=response.stop_reason or "stop",
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                ),
            )
        except anthropic.APIStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest, model: str
    ) -> AsyncGenerator[str, None]:
        system_prompt, messages = self._build_messages(request)
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())

        try:
            kwargs = dict(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens or 4096,
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature

            import orjson

            async with self.client.messages.stream(**kwargs) as stream:
                # First chunk: role
                first_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                    ],
                }
                yield self._sse_line(orjson.dumps(first_chunk).decode())

                async for text in stream.text_stream:
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {"index": 0, "delta": {"content": text}, "finish_reason": None}
                        ],
                    }
                    yield self._sse_line(orjson.dumps(chunk).decode())

                # Final chunk
                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield self._sse_line(orjson.dumps(final_chunk).decode())
                yield self._sse_done()

        except anthropic.APIStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
