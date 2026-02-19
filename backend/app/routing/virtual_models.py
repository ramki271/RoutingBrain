"""
Virtual Model Registry

Resolves abstract rb:// identifiers to concrete model + provider pairs.
Policies only reference virtual IDs — swap real models by editing models.yaml,
never touching routing policy YAML files.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)

VIRTUAL_PREFIX = "rb://"


@dataclass
class ResolvedModel:
    virtual_id: str
    model: str
    provider: str
    description: str = ""


class VirtualModelRegistry:
    def __init__(self, models_config_path: str):
        self._registry: dict[str, ResolvedModel] = {}
        self._load(models_config_path)

    def _load(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            logger.warning("models_config_missing", path=path)
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        virtual = data.get("virtual_models", {})
        for virtual_id, mapping in virtual.items():
            self._registry[virtual_id] = ResolvedModel(
                virtual_id=virtual_id,
                model=mapping["model"],
                provider=mapping["provider"],
                description=mapping.get("description", ""),
            )

        logger.info("virtual_models_loaded", count=len(self._registry))

    def resolve(self, model_id: str) -> tuple[str, str]:
        """
        Resolve a model_id to (model, provider).
        If model_id starts with rb://, look up in registry.
        Otherwise treat it as a literal model name and infer provider.
        Returns (model, provider).
        """
        if model_id.startswith(VIRTUAL_PREFIX):
            entry = self._registry.get(model_id)
            if entry:
                return entry.model, entry.provider
            logger.warning("virtual_model_not_found", virtual_id=model_id)
            # Fallback to a safe default rather than crashing
            return "claude-haiku-4-5-20251001", "anthropic"

        # Literal model name — infer provider
        return model_id, self._infer_provider(model_id)

    def _infer_provider(self, model: str) -> str:
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return "openai"
        if model.startswith("gemini"):
            return "gemini"
        if any(x in model.lower() for x in ["llama", "codellama", "deepseek", "mistral", "phi"]):
            return "ollama"
        return "openai"

    def resolve_list(self, model_ids: list[str]) -> list[str]:
        """Resolve a list of virtual/literal IDs to concrete model names."""
        return [self.resolve(m)[0] for m in model_ids]

    def get_all(self) -> dict[str, ResolvedModel]:
        return dict(self._registry)

    def is_virtual(self, model_id: str) -> bool:
        return model_id.startswith(VIRTUAL_PREFIX)
