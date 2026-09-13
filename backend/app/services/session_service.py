import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import ConversationTurn
from app.core.errors import NotFoundError
from app.models import Artifact, ChatSession, Message
from app.retrieval.retriever import RetrievedChunk


async def create_session(db: AsyncSession, *, title: str = "New chat") -> ChatSession:
    session = ChatSession(title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession) -> list[ChatSession]:
    result = await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return session


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    session = await get_session(db, session_id)
    await db.delete(session)
    await db.commit()


async def list_messages(db: AsyncSession, session_id: uuid.UUID) -> list[Message]:
    await get_session(db, session_id)  # 404s if missing
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def list_artifacts(db: AsyncSession, session_id: uuid.UUID) -> list[Artifact]:
    await get_session(db, session_id)  # 404s if missing
    result = await db.execute(
        select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at)
    )
    return list(result.scalars().all())


async def get_conversation_turns(db: AsyncSession, session_id: uuid.UUID) -> list[ConversationTurn]:
    messages = await list_messages(db, session_id)
    return [ConversationTurn(role=m.role, content=m.content) for m in messages]


def _sources_to_json(sources: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "chunk_id": s.chunk_id,
            "episode_title": s.episode_title,
            "guest": s.guest,
            "url": s.url,
            "excerpt": s.content[:400],
            "score": round(s.score, 4),
        }
        for s in sources
    ]


async def add_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    role: str,
    content: str,
    model: str | None = None,
    provider: str | None = None,
    sources: list[RetrievedChunk] | None = None,
    metadata: dict | None = None,
) -> Message:
    session = await get_session(db, session_id)
    message = Message(
        session_id=session.id,
        role=role,
        content=content,
        model=model,
        provider=provider,
        sources=_sources_to_json(sources or []),
        message_metadata=metadata or {},
    )
    db.add(message)

    # Auto-title new sessions from the first user message so the sidebar is immediately useful.
    if role == "user" and session.title == "New chat":
        session.title = (content[:60] + "...") if len(content) > 60 else content

    await db.commit()
    await db.refresh(message)
    return message
