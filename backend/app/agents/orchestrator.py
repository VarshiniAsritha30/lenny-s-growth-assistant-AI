import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.router import Intent, classify_intent
from app.agents.skills.artifact_generation import generate_artifact
from app.agents.skills.grounded_qa import answer_grounded_question
from app.agents.skills.ship30 import generate_ship30_essay
from app.core.logging import Events, get_logger
from app.models import Artifact, Message
from app.providers.base import EmbeddingProvider, LLMProvider
from app.retrieval.retriever import RetrievedChunk, Retriever
from app.services import artifact_service, session_service

logger = get_logger(__name__)


@dataclass
class OrchestratorResult:
    assistant_message: Message
    sources: list[RetrievedChunk] = field(default_factory=list)
    artifact: Artifact | None = None
    intent: Intent = Intent.GROUNDED_QA


async def handle_user_message(
    db: AsyncSession,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    session_id: uuid.UUID,
    user_text: str,
) -> OrchestratorResult:
    started = time.monotonic()
    logger.info(Events.REQUEST_STARTED, session_id=str(session_id), operation="handle_message")

    history = await session_service.get_conversation_turns(db, session_id)
    await session_service.add_message(db, session_id, role="user", content=user_text)

    intent = classify_intent(user_text)
    retriever = Retriever(db, embedder)

    artifact: Artifact | None = None

    try:
        if intent == Intent.SHIP30_ESSAY:
            essay = await generate_ship30_essay(llm=llm, retriever=retriever, history=history, topic=user_text)
            content = f"# {essay.title}\n\n{essay.body_markdown}"
            sources = essay.sources
            reply_text = content
            if essay.sources:
                artifact = await artifact_service.create_artifact(
                    db,
                    session_id=session_id,
                    message_id=None,
                    artifact_type="markdown",
                    title=essay.title,
                    content=content,
                    sources=essay.sources,
                )

        elif intent in (Intent.ARTIFACT_MARKDOWN, Intent.ARTIFACT_HTML):
            artifact_type = "html" if intent == Intent.ARTIFACT_HTML else "markdown"
            generated = await generate_artifact(
                llm=llm, retriever=retriever, history=history, request=user_text, artifact_type=artifact_type
            )
            sources = generated.sources
            reply_text = f"I've generated the {artifact_type} artifact **{generated.title}** — see the Artifact panel."
            artifact = await artifact_service.create_artifact(
                db,
                session_id=session_id,
                message_id=None,
                artifact_type=generated.type,
                title=generated.title,
                content=generated.content,
                sources=generated.sources,
            )

        else:
            answer = await answer_grounded_question(llm=llm, retriever=retriever, history=history, question=user_text)
            reply_text = answer.text
            sources = answer.sources

    except Exception:
        logger.error(Events.MODEL_FAILED, session_id=str(session_id), intent=intent.value)
        raise

    logger.info(
        Events.RETRIEVAL_COMPLETED,
        session_id=str(session_id),
        intent=intent.value,
        retrieval_count=len(sources),
    )

    assistant_message = await session_service.add_message(
        db,
        session_id,
        role="assistant",
        content=reply_text,
        model=getattr(llm, "model", None),
        provider=llm.name,
        sources=sources,
        metadata={"intent": intent.value},
    )

    if artifact is not None:
        artifact.message_id = assistant_message.id
        await db.commit()
        # onupdate=func.now() on Artifact.updated_at means the new value is server-generated;
        # without a refresh here, the ORM leaves that attribute in a lazy-load state that
        # Pydantic's synchronous serialization can't resolve (MissingGreenlet).
        await db.refresh(artifact)

    latency_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        Events.REQUEST_COMPLETED,
        session_id=str(session_id),
        intent=intent.value,
        provider=llm.name,
        latency_ms=latency_ms,
        status="ok",
    )

    return OrchestratorResult(assistant_message=assistant_message, sources=sources, artifact=artifact, intent=intent)
