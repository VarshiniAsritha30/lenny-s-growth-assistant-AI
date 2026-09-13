from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, sourced entirely from environment variables.

    No component should read os.environ directly - everything flows through here so the
    provider/config surface is auditable in one place.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://postgres:lenny_dev_password@127.0.0.1:5544/lenny_growth_assistant"
    )

    # --- LLM provider selection ---
    llm_provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    embedding_provider: Literal["ollama", "openai"] = "ollama"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_embedding_model: str = "nomic-embed-text"

    # --- Anthropic ---
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # --- OpenAI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Retrieval ---
    embedding_dimensions: int = 768  # nomic-embed-text output size
    retrieval_top_k: int = 6
    # Calibrated against nomic-embed-text: on-topic queries score ~0.58-0.65 raw cosine
    # similarity against this corpus, off-topic queries plateau around ~0.42-0.53. This is
    # necessarily corpus/embedding-model specific - re-calibrate if you swap either.
    retrieval_min_score: float = 0.55

    # --- Ship 30 essay ---
    ship30_target_words: int = 1250

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
