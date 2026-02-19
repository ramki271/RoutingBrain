import time
import uuid
from typing import AsyncGenerator

from google import genai
from google.genai import types

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


class GeminiProvider(BaseProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def _build_contents(self, request: ChatCompletionRequest):
        system_prompt = None
        contents = []
        for msg in request.messages:
            if msg.role == "system":
                system_prompt = msg.text_content()
            elif msg.role == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=msg.text_content())]))
            elif msg.role == "assistant":
                contents.append(types.Content(role="model", parts=[types.Part(text=msg.text_content())]))
        return system_prompt, contents

    async def chat_completion(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        try:
            system_prompt, contents = self._build_contents(request)
            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                system_instruction=system_prompt,
            )
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            text = response.text or ""
            usage = response.usage_metadata
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                object="chat.completion",
                created=int(time.time()),
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessageDelta(role="assistant", content=text),
                        finish_reason="stop",
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=usage.prompt_token_count or 0,
                    completion_tokens=usage.candidates_token_count or 0,
                    total_tokens=usage.total_token_count or 0,
                ) if usage else None,
            )
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest, model: str
    ) -> AsyncGenerator[str, None]:
        import orjson

        try:
            system_prompt, contents = self._build_contents(request)
            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                system_instruction=system_prompt,
            )
            chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())

            async for chunk in await self.client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            ):
                text = chunk.text or ""
                if text:
                    data = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                    }
                    yield self._sse_line(orjson.dumps(data).decode())

            final = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield self._sse_line(orjson.dumps(final).decode())
            yield self._sse_done()

        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def health_check(self) -> bool:
        try:
            models = []
            async for m in await self.client.aio.models.list():
                models.append(m)
            return True
        except Exception:
            return False
