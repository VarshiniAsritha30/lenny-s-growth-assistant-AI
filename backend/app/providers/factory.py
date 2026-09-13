from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.runtime_state import get_active_provider_name
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.ollama import OllamaEmbeddingProvider, OllamaProvider
from app.providers.openai_provider import OpenAIEmbeddingProvider, OpenAIProvider


def build_llm_provider(settings: Settings | None = None, *, provider_name: str | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider_name = provider_name or get_active_provider_name(settings.llm_provider)
    if provider_name == "ollama":
        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
    if provider_name == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    raise ValueError(f"Unknown provider: {provider_name}")


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider}")


@lru_cache
def get_llm_provider() -> LLMProvider:
    return build_llm_provider()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider()


def clear_provider_cache() -> None:
    get_llm_provider.cache_clear()
    get_embedding_provider.cache_clear()
