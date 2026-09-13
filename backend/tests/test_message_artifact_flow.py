import pytest

from app.models import Embedding, Transcript, TranscriptChunk
from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider


async def _seed_chunk_matching(db_session, text: str) -> None:
    transcript = Transcript(title="Seed", content=text, content_hash=f"hash-{text}")
    db_session.add(transcript)
    await db_session.flush()
    chunk = TranscriptChunk(transcript_id=transcript.id, chunk_index=0, content=text, token_count=5)
    db_session.add(chunk)
    await db_session.flush()
    db_session.add(Embedding(chunk_id=chunk.id, embedding=[0.0] * 768, model="fake"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_html_artifact_request_via_message_endpoint_serializes_cleanly(
    client, override_llm, override_embedder, db_session
):
    """Regression test: after handle_user_message links an artifact to its assistant message
    and commits, the ORM leaves onupdate=func.now() columns (Artifact.updated_at) in a
    lazy-load state. Serializing the response with Pydantic outside of an awaited context used
    to raise MissingGreenlet. A refresh() after that commit is required.
    """
    await _seed_chunk_matching(db_session, "retention best practices content")
    override_llm(FakeLLMProvider(response="<!DOCTYPE html><html><body><h1>Retention</h1></body></html>"))
    override_embedder(FakeEmbeddingProvider())

    session_id = (await client.post("/api/sessions", json={})).json()["id"]
    resp = await client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Create an html artifact one-pager about retention"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["artifact"] is not None
    assert body["artifact"]["type"] == "html"
    assert body["artifact"]["message_id"] == body["assistant_message"]["id"]
    assert body["artifact"]["updated_at"] is not None
