import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import Events, get_logger
from app.models import Artifact
from app.retrieval.retriever import RetrievedChunk

logger = get_logger(__name__)


async def create_artifact(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    message_id: uuid.UUID | None,
    artifact_type: str,
    title: str,
    content: str,
    sources: list[RetrievedChunk],
) -> Artifact:
    artifact = Artifact(
        session_id=session_id,
        message_id=message_id,
        type=artifact_type,
        title=title,
        content=content,
        sources=[{"episode_title": s.episode_title, "url": s.url} for s in sources],
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    logger.info(Events.ARTIFACT_CREATED, artifact_id=str(artifact.id), type=artifact_type)
    return artifact


async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID) -> Artifact:
    artifact = await db.get(Artifact, artifact_id)
    if artifact is None:
        raise NotFoundError(f"Artifact {artifact_id} not found")
    return artifact
