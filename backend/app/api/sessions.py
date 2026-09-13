import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.schemas import ArtifactOut, MessageOut, SessionCreate, SessionOut
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)) -> SessionOut:
    session = await session_service.create_session(db, title=body.title)
    return SessionOut.model_validate(session)


@router.get("", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionOut]:
    sessions = await session_service.list_sessions(db)
    return [SessionOut.model_validate(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SessionOut:
    session = await session_service.get_session(db, session_id)
    return SessionOut.model_validate(session)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await session_service.delete_session(db, session_id)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[MessageOut]:
    messages = await session_service.list_messages(db, session_id)
    return [MessageOut.model_validate(m) for m in messages]


@router.get("/{session_id}/artifacts", response_model=list[ArtifactOut])
async def list_session_artifacts(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[ArtifactOut]:
    artifacts = await session_service.list_artifacts(db, session_id)
    return [ArtifactOut.model_validate(a) for a in artifacts]
