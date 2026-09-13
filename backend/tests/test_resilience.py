import pytest

from app.core.errors import ProviderConfigError
from app.models import Embedding, Transcript, TranscriptChunk
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.ollama import OllamaProvider
from tests.conftest import FakeEmbeddingProvider


async def _seed_one_chunk(db_session) -> None:
    """Insert a chunk that's guaranteed to be retrieved via full-text search regardless of
    embedding quality, so the test can reach the LLM call (and its failure) instead of short-
    circuiting on "no supporting context found".
    """
    transcript = Transcript(
        title="Seed Episode",
        content="hello world transcript content",
        content_hash="seed-hash-resilience-test",
    )
    db_session.add(transcript)
    await db_session.flush()
    chunk = TranscriptChunk(transcript_id=transcript.id, chunk_index=0, content="hello world", token_count=2)
    db_session.add(chunk)
    await db_session.flush()
    db_session.add(Embedding(chunk_id=chunk.id, embedding=[0.0] * 768, model="fake"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_message_endpoint_returns_503_when_ollama_unreachable(client, override_llm, override_embedder, db_session):
    await _seed_one_chunk(db_session)
    # Point at a port nothing is listening on to simulate "Ollama not running".
    override_llm(OllamaProvider("http://localhost:19999", "llama3.2:1b"))
    override_embedder(FakeEmbeddingProvider())

    session_id = (await client.post("/api/sessions", json={})).json()["id"]
    resp = await client.post(f"/api/sessions/{session_id}/messages", json={"content": "hello"})

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "MODEL_UNAVAILABLE"
    assert "ollama" in body["error"]["message"].lower() or "model" in body["error"]["message"].lower()


def test_anthropic_provider_without_api_key_raises_config_error_not_crash():
    with pytest.raises(ProviderConfigError):
        AnthropicProvider(api_key=None, model="claude-sonnet-4-5-20250929")


@pytest.mark.asyncio
async def test_models_select_with_missing_key_returns_structured_error(client):
    resp = await client.post("/api/models/select", json={"provider": "anthropic"})
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "PROVIDER_CONFIG_ERROR"

    # Switching back to ollama must still work afterwards (no corrupted global state).
    resp = await client.post("/api/models/select", json={"provider": "ollama"})
    assert resp.status_code == 200
    assert resp.json()["provider"] == "ollama"
