import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import Events, get_logger
from app.models import Embedding, Transcript, TranscriptChunk
from app.providers.base import EmbeddingProvider
from app.retrieval.chunker import chunk_text

logger = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class ParsedTranscript:
    title: str
    guest: str | None
    url: str | None
    published_at: datetime | None
    content: str
    source_type: str


def parse_transcript_file(path: Path) -> ParsedTranscript:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return ParsedTranscript(
            title=path.stem, guest=None, url=None, published_at=None, content=raw.strip(), source_type="local"
        )

    front_raw, body = match.groups()
    front = yaml.safe_load(front_raw) or {}

    published_at = None
    if front.get("published_at"):
        published_at = datetime.fromisoformat(str(front["published_at"]))

    title = str(front.get("title", path.stem))
    return ParsedTranscript(
        title=title,
        guest=front.get("guest"),
        url=front.get("url"),
        published_at=published_at,
        content=body.strip(),
        source_type="demo" if "[DEMO]" in title else "local",
    )


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class IngestionResult:
    transcripts_seen: int = 0
    transcripts_created: int = 0
    transcripts_skipped_duplicate: int = 0
    chunks_created: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


class IngestionService:
    """Loads transcript files from disk, deduplicates by content hash, chunks, embeds, and
    stores everything with full provenance (episode title, guest, url, chunk index) so the
    retrieval layer can always cite its sources.
    """

    def __init__(self, db: AsyncSession, embedder: EmbeddingProvider) -> None:
        self.db = db
        self.embedder = embedder

    async def ingest_directory(self, directory: Path) -> IngestionResult:
        result = IngestionResult()
        files = sorted(
            f
            for f in [*directory.glob("*.md"), *directory.glob("*.txt")]
            if f.name.upper() != "README.MD"
        )

        for path in files:
            result.transcripts_seen += 1
            try:
                await self._ingest_file(path, result)
            except Exception as exc:  # noqa: BLE001 - ingestion must keep going on a bad file
                logger.error(Events.INGESTION_FAILED, file=str(path), error=str(exc))
                result.errors.append(f"{path.name}: {exc}")

        await self.db.commit()
        return result

    async def _ingest_file(self, path: Path, result: IngestionResult) -> None:
        parsed = parse_transcript_file(path)
        chash = content_hash(parsed.content)

        existing = (
            await self.db.execute(select(Transcript).where(Transcript.content_hash == chash))
        ).scalar_one_or_none()
        if existing is not None:
            result.transcripts_skipped_duplicate += 1
            return

        transcript = Transcript(
            title=parsed.title,
            guest=parsed.guest,
            url=parsed.url,
            published_at=parsed.published_at,
            content=parsed.content,
            content_hash=chash,
            source_type=parsed.source_type,
        )
        self.db.add(transcript)
        await self.db.flush()  # assigns transcript.id

        chunks = chunk_text(parsed.content)
        if not chunks:
            return

        embeddings = await self.embedder.embed([c.content for c in chunks])

        for chunk, vector in zip(chunks, embeddings, strict=True):
            db_chunk = TranscriptChunk(
                transcript_id=transcript.id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                chunk_metadata={"episode_title": parsed.title, "guest": parsed.guest, "url": parsed.url},
            )
            self.db.add(db_chunk)
            await self.db.flush()

            embedder_model = getattr(self.embedder, "model", self.embedder.name)
            self.db.add(Embedding(chunk_id=db_chunk.id, embedding=vector, model=embedder_model))
            result.chunks_created += 1
            logger.info(
                Events.INGESTION_CHUNK_STORED,
                transcript_id=str(transcript.id),
                chunk_index=chunk.index,
            )

        result.transcripts_created += 1
