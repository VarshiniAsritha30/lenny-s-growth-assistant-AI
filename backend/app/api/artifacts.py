import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills.artifact_generation import generate_artifact
from app.api.deps import get_db, get_embedding_provider, get_llm_provider
from app.providers.base import EmbeddingProvider, LLMProvider
from app.retrieval.retriever import Retriever
from app.schemas.schemas import ArtifactCreateRequest, ArtifactOut
from app.services import artifact_service, session_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.post("", response_model=ArtifactOut, status_code=201)
async def create_artifact_endpoint(
    body: ArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> ArtifactOut:
    await session_service.get_session(db, body.session_id)
    history = await session_service.get_conversation_turns(db, body.session_id)
    retriever = Retriever(db, embedder)

    generated = await generate_artifact(
        llm=llm, retriever=retriever, history=history, request=body.request, artifact_type=body.type
    )
    artifact = await artifact_service.create_artifact(
        db,
        session_id=body.session_id,
        message_id=None,
        artifact_type=generated.type,
        title=generated.title,
        content=generated.content,
        sources=generated.sources,
    )
    return ArtifactOut.model_validate(artifact)


@router.get("/{artifact_id}", response_model=ArtifactOut)
async def get_artifact_endpoint(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ArtifactOut:
    artifact = await artifact_service.get_artifact(db, artifact_id)
    return ArtifactOut.model_validate(artifact)
