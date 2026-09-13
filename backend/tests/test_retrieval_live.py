from pathlib import Path

import pytest

from app.providers.ollama import OllamaEmbeddingProvider
from app.retrieval.retriever import Retriever
from app.services.ingestion import IngestionService
from tests.conftest import requires_ollama

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_transcripts"


@requires_ollama
@pytest.mark.asyncio
async def test_relevant_query_returns_grounded_chunks_with_real_embeddings(db_session):
    embedder = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text", 768)
    await IngestionService(db_session, embedder).ingest_directory(SAMPLE_DIR)

    retriever = Retriever(db_session, embedder)
    results = await retriever.retrieve("How should I think about improving activation and onboarding?")

    assert len(results) > 0
    assert any("activation" in r.episode_title.lower() for r in results)
    assert all(r.score >= 0 for r in results)


@requires_ollama
@pytest.mark.asyncio
async def test_off_topic_query_returns_no_supported_chunks(db_session):
    embedder = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text", 768)
    await IngestionService(db_session, embedder).ingest_directory(SAMPLE_DIR)

    retriever = Retriever(db_session, embedder)
    results = await retriever.retrieve("What is the boiling point of liquid nitrogen in kelvin?")

    assert results == []
