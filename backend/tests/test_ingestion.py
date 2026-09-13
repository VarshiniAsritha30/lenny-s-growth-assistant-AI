from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Embedding, Transcript, TranscriptChunk
from app.services.ingestion import IngestionService, content_hash, parse_transcript_file


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_transcript_file_extracts_frontmatter(tmp_path):
    path = _write(
        tmp_path,
        "ep1.md",
        "---\ntitle: '[DEMO] Test Episode'\nguest: Jane Doe\nurl: https://example.com/ep1\n"
        "published_at: 2024-01-15\n---\n\nBody paragraph one.\n\nBody paragraph two.",
    )
    parsed = parse_transcript_file(path)

    assert parsed.title == "[DEMO] Test Episode"
    assert parsed.guest == "Jane Doe"
    assert parsed.url == "https://example.com/ep1"
    assert parsed.published_at.year == 2024
    assert parsed.source_type == "demo"
    assert "Body paragraph one." in parsed.content


def test_parse_transcript_file_without_frontmatter_falls_back_gracefully(tmp_path):
    path = _write(tmp_path, "plain.txt", "Just raw transcript text, no frontmatter at all.")
    parsed = parse_transcript_file(path)

    assert parsed.title == "plain"
    assert parsed.source_type == "local"
    assert parsed.content == "Just raw transcript text, no frontmatter at all."


def test_content_hash_is_stable_and_content_sensitive():
    assert content_hash("hello") == content_hash("hello")
    assert content_hash("hello") != content_hash("hello!")


@pytest.mark.asyncio
async def test_ingest_directory_creates_transcripts_chunks_and_embeddings(tmp_path, db_session, fake_embedder):
    _write(
        tmp_path,
        "ep1.md",
        "---\ntitle: Episode One\nguest: A Guest\n---\n\n" + ("Paragraph about growth. " * 30 + "\n\n") * 3,
    )
    _write(tmp_path, "README.md", "This should be skipped, not ingested as a transcript.")

    service = IngestionService(db_session, fake_embedder)
    result = await service.ingest_directory(tmp_path)

    assert result.transcripts_seen == 1  # README excluded
    assert result.transcripts_created == 1
    assert result.chunks_created > 0
    assert result.errors == []

    transcripts = (await db_session.execute(select(Transcript))).scalars().all()
    assert len(transcripts) == 1
    assert transcripts[0].title == "Episode One"

    chunks = (await db_session.execute(select(TranscriptChunk))).scalars().all()
    embeddings = (await db_session.execute(select(Embedding))).scalars().all()
    assert len(chunks) == result.chunks_created
    assert len(embeddings) == result.chunks_created


@pytest.mark.asyncio
async def test_ingest_directory_skips_duplicate_content_on_second_run(tmp_path, db_session, fake_embedder):
    _write(tmp_path, "ep1.md", "---\ntitle: Episode One\n---\n\n" + "Some content here. " * 20)

    service = IngestionService(db_session, fake_embedder)
    first = await service.ingest_directory(tmp_path)
    second = await service.ingest_directory(tmp_path)

    assert first.transcripts_created == 1
    assert second.transcripts_created == 0
    assert second.transcripts_skipped_duplicate == 1
