from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    log_level: str = "INFO"

    # Auth
    valid_api_keys: str = "rb-dev-key-1"

    # Provider keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8000"

    # Database
    database_url: str = "postgresql+asyncpg://routingbrain:routingbrain@localhost:5432/routingbrain"
    redis_url: str = "redis://localhost:6379/0"

    # Routing brain
    routing_brain_model: str = "claude-haiku-4-5-20251001"
    routing_brain_timeout_seconds: int = 3
    routing_brain_confidence_threshold: float = 0.6

    # Config paths
    models_config_path: str = "config/models.yaml"
    settings_config_path: str = "config/settings.yaml"
    routing_policies_dir: str = "config/routing_policies"
    meta_llm_system_prompt_path: str = "config/meta_llm_system_prompt.txt"

    @property
    def api_keys_list(self) -> List[str]:
        return [k.strip() for k in self.valid_api_keys.split(",") if k.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
