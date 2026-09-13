from fastapi import APIRouter

from app.core.config import get_settings
from app.core.runtime_state import get_active_provider_name, set_active_provider_name
from app.providers.factory import build_llm_provider, clear_provider_cache
from app.schemas.schemas import ModelInfo, ModelSelectRequest

router = APIRouter(prefix="/api/models", tags=["models"])

_ALL_PROVIDERS = ["ollama", "anthropic", "openai"]


@router.get("", response_model=list[ModelInfo])
async def list_models() -> list[ModelInfo]:
    settings = get_settings()
    active = get_active_provider_name(settings.llm_provider)
    results = []

    for name in _ALL_PROVIDERS:
        model_name = {
            "ollama": settings.ollama_model,
            "anthropic": settings.anthropic_model,
            "openai": settings.openai_model,
        }[name]
        try:
            provider = build_llm_provider(settings, provider_name=name)
            healthy, detail = await provider.health_check()
        except Exception as exc:  # noqa: BLE001 - config errors (missing key) are expected here
            healthy, detail = False, str(exc)

        results.append(
            ModelInfo(provider=name, model=model_name, is_active=(name == active), is_healthy=healthy, detail=detail)
        )
    return results


@router.post("/select", response_model=ModelInfo)
async def select_model(body: ModelSelectRequest) -> ModelInfo:
    settings = get_settings()
    provider = build_llm_provider(settings, provider_name=body.provider)  # raises if misconfigured
    set_active_provider_name(body.provider)
    clear_provider_cache()

    healthy, detail = await provider.health_check()
    model_name = getattr(provider, "model", "")
    return ModelInfo(provider=body.provider, model=model_name, is_active=True, is_healthy=healthy, detail=detail)
