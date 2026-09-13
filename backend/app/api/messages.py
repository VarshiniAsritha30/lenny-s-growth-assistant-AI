import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import handle_user_message
from app.api.deps import get_db, get_embedding_provider, get_llm_provider
from app.providers.base import EmbeddingProvider, LLMProvider
from app.schemas.schemas import ArtifactOut, MessageCreate, MessageOut, SendMessageResponse, SourceOut
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["messages"])


@router.post("/{session_id}/messages", response_model=SendMessageResponse, status_code=201)
async def send_message(
    session_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> SendMessageResponse:
    await session_service.get_session(db, session_id)  # 404s early if session doesn't exist

    result = await handle_user_message(db, llm, embedder, session_id, body.content)

    messages = await session_service.list_messages(db, session_id)
    user_message = messages[-2] if len(messages) >= 2 else messages[-1]

    return SendMessageResponse(
        user_message=MessageOut.model_validate(user_message),
        assistant_message=MessageOut.model_validate(result.assistant_message),
        sources=[
            SourceOut(
                chunk_id=s.chunk_id,
                episode_title=s.episode_title,
                guest=s.guest,
                url=s.url,
                excerpt=s.content[:400],
                score=s.score,
            )
            for s in result.sources
        ],
        artifact=ArtifactOut.model_validate(result.artifact) if result.artifact else None,
        intent=result.intent.value,
    )
