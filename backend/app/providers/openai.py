import time
import uuid
from typing import AsyncGenerator

import openai as openai_lib

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


class OpenAIProvider(BaseProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, base_url: str = None):
        self.client = openai_lib.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def _build_messages(self, request: ChatCompletionRequest) -> list:
        return [
            {"role": msg.role, "content": msg.text_content()}
            for msg in request.messages
        ]

    async def chat_completion(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        try:
            kwargs = dict(
                model=model,
                messages=self._build_messages(request),
                stream=False,
            )
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens
            if request.top_p is not None:
                kwargs["top_p"] = request.top_p

            response = await self.client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            return ChatCompletionResponse(
                id=response.id,
                object="chat.completion",
                created=response.created,
                model=model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessageDelta(
                            role="assistant",
                            content=choice.message.content,
                        ),
                        finish_reason=choice.finish_reason,
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ) if response.usage else None,
            )
        except openai_lib.APIStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest, model: str
    ) -> AsyncGenerator[str, None]:
        import orjson

        try:
            kwargs = dict(
                model=model,
                messages=self._build_messages(request),
                stream=True,
            )
            if request.temperature is not None:
                kwargs["temperature"] = request.temperature
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens

            async with await self.client.chat.completions.create(**kwargs) as stream:
                async for chunk in stream:
                    yield self._sse_line(orjson.dumps(chunk.model_dump()).decode())
                yield self._sse_done()

        except openai_lib.APIStatusError as e:
            raise ProviderError(str(e), self.provider_name, e.status_code)
        except Exception as e:
            raise ProviderError(str(e), self.provider_name)

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
