import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    chunk_id: str
    episode_title: str
    guest: str | None
    url: str | None
    excerpt: str
    score: float


class SessionCreate(BaseModel):
    title: str = "New chat"


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    model: str | None
    provider: str | None
    sources: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID | None
    type: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SendMessageResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    sources: list[SourceOut]
    artifact: ArtifactOut | None = None
    intent: str


class Ship30Request(BaseModel):
    session_id: uuid.UUID
    topic: str = Field(min_length=1, max_length=500)


class ArtifactCreateRequest(BaseModel):
    session_id: uuid.UUID
    request: str = Field(min_length=1, max_length=2000)
    type: str = Field(pattern="^(markdown|html)$")


class ModelInfo(BaseModel):
    provider: str
    model: str
    is_active: bool
    is_healthy: bool
    detail: str


class ModelSelectRequest(BaseModel):
    provider: str = Field(pattern="^(ollama|anthropic|openai)$")


class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str = Field(pattern="^(up|down)$")
    comment: str | None = None


class HealthOut(BaseModel):
    status: str
    detail: dict[str, str] = {}
