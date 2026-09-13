#!/usr/bin/env python3
"""Ingest transcript files into the knowledge base.

Usage:
    python scripts/ingest_transcripts.py --source data/sample_transcripts

Pipeline: load .md/.txt files -> normalize/parse frontmatter -> deduplicate by content hash
-> chunk -> embed -> store with provenance metadata (episode title, guest, url, chunk index).
Safe to re-run: files whose content hash already exists are skipped, not re-embedded.
"""
import argparse
import asyncio
import sys
from pathlib import Path

try:
    import app  # noqa: F401  - already importable (e.g. PYTHONPATH=/app inside the Docker image)
except ImportError:
    BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.providers.factory import get_embedding_provider  # noqa: E402
from app.services.ingestion import IngestionService  # noqa: E402

logger = get_logger("ingest")


async def main(source: Path) -> int:
    if not source.exists():
        print(f"Source directory does not exist: {source}", file=sys.stderr)
        return 1

    embedder = get_embedding_provider()
    ok, detail = await embedder.health_check()
    if not ok:
        print(f"Embedding provider unavailable: {detail}", file=sys.stderr)
        return 1
    print(f"Embedding provider ready: {detail}")

    async with AsyncSessionLocal() as db:
        service = IngestionService(db, embedder)
        result = await service.ingest_directory(source)

    print("\n--- Ingestion summary ---")
    print(f"Transcript files seen:        {result.transcripts_seen}")
    print(f"Transcripts newly ingested:   {result.transcripts_created}")
    print(f"Transcripts skipped (dup):    {result.transcripts_skipped_duplicate}")
    print(f"Chunks created:               {result.chunks_created}")
    if result.errors:
        print(f"Errors ({len(result.errors)}):")
        for err in result.errors:
            print(f"  - {err}")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "sample_transcripts",
        help="Directory of .md/.txt transcript files (default: data/sample_transcripts)",
    )
    args = parser.parse_args()

    configure_logging("INFO")
    exit_code = asyncio.run(main(args.source))
    sys.exit(exit_code)
