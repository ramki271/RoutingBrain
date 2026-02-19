import asyncio
from typing import Dict, Optional

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.anthropic import AnthropicProvider
from app.providers.base import BaseProvider
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai import OpenAIProvider

logger = get_logger(__name__)


class ProviderRegistry:
    """Factory and registry for all LLM provider adapters."""

    def __init__(self, settings: Settings):
        self._providers: Dict[str, BaseProvider] = {}
        self._settings = settings
        self._init_providers()

    def _init_providers(self) -> None:
        if self._settings.anthropic_api_key:
            self._providers["anthropic"] = AnthropicProvider(
                api_key=self._settings.anthropic_api_key
            )
            logger.info("provider_registered", provider="anthropic")

        if self._settings.openai_api_key:
            self._providers["openai"] = OpenAIProvider(
                api_key=self._settings.openai_api_key
            )
            logger.info("provider_registered", provider="openai")

        if self._settings.gemini_api_key:
            self._providers["gemini"] = GeminiProvider(
                api_key=self._settings.gemini_api_key
            )
            logger.info("provider_registered", provider="gemini")

        # Ollama is always available (local)
        self._providers["ollama"] = OllamaProvider(
            base_url=self._settings.ollama_base_url
        )
        logger.info("provider_registered", provider="ollama")

        # vLLM uses OpenAI-compatible API
        if self._settings.vllm_base_url:
            self._providers["vllm"] = OpenAIProvider(
                api_key="not-needed",
                base_url=self._settings.vllm_base_url,
            )
            logger.info("provider_registered", provider="vllm")

    def get(self, provider_name: str) -> Optional[BaseProvider]:
        return self._providers.get(provider_name)

    def available_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def health_check_all(self) -> Dict[str, bool]:
        async def _check(name: str, provider: BaseProvider) -> tuple[str, bool]:
            try:
                ok = await asyncio.wait_for(provider.health_check(), timeout=3.0)
                return name, ok
            except Exception:
                return name, False

        checks = await asyncio.gather(*[_check(n, p) for n, p in self._providers.items()])
        return dict(checks)
