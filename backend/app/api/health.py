from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_llm_provider
from app.providers.base import LLMProvider
from app.providers.factory import get_embedding_provider
from app.schemas.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/health/ready", response_model=HealthOut)
async def health_ready(
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> HealthOut:
    detail: dict[str, str] = {}
    overall_ok = True

    try:
        await db.execute(text("SELECT 1"))
        detail["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        detail["database"] = f"unavailable: {exc}"
        overall_ok = False

    llm_ok, llm_detail = await llm.health_check()
    detail["llm_provider"] = llm_detail
    overall_ok = overall_ok and llm_ok

    embed_ok, embed_detail = await get_embedding_provider().health_check()
    detail["embedding_provider"] = embed_detail
    overall_ok = overall_ok and embed_ok

    return HealthOut(status="ok" if overall_ok else "degraded", detail=detail)
