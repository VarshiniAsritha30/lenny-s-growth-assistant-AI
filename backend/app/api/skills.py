from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills.ship30 import generate_ship30_essay
from app.api.deps import get_db, get_embedding_provider, get_llm_provider
from app.providers.base import EmbeddingProvider, LLMProvider
from app.retrieval.retriever import Retriever
from app.schemas.schemas import ArtifactOut, Ship30Request
from app.services import artifact_service, session_service

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/ship30", response_model=ArtifactOut, status_code=201)
async def ship30(
    body: Ship30Request,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> ArtifactOut:
    await session_service.get_session(db, body.session_id)
    history = await session_service.get_conversation_turns(db, body.session_id)
    retriever = Retriever(db, embedder)

    essay = await generate_ship30_essay(llm=llm, retriever=retriever, history=history, topic=body.topic)
    content = f"# {essay.title}\n\n{essay.body_markdown}"

    artifact = await artifact_service.create_artifact(
        db,
        session_id=body.session_id,
        message_id=None,
        artifact_type="markdown",
        title=essay.title,
        content=content,
        sources=essay.sources,
    )
    return ArtifactOut.model_validate(artifact)
