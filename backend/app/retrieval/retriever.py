from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.providers.base import EmbeddingProvider


@dataclass
class RetrievedChunk:
    chunk_id: str
    transcript_id: str
    episode_title: str
    guest: str | None
    url: str | None
    chunk_index: int
    content: str
    score: float  # raw cosine similarity where available - the groundedness signal
    matched_lexically: bool  # hit Postgres full-text search, independent of vector score


# Hybrid retrieval: pgvector cosine similarity ("semantic" hits) reciprocal-rank-fused with
# Postgres full-text search ("lexical" hits, catches exact terms/names the embedding model
# under-weights) for *ranking order*. Groundedness (is this actually relevant, or is the
# assistant about to hallucinate on top of noise?) is judged on the raw cosine similarity, not
# the fused rank - a fused/normalized score always has a "1.0" top result even when every
# candidate is irrelevant, which would silently defeat the refusal behavior.
_VECTOR_SQL = text(
    """
    SELECT c.id AS chunk_id, c.transcript_id, c.chunk_index, c.content,
           t.title AS episode_title, t.guest, t.url,
           1 - (e.embedding <=> CAST(:query_embedding AS vector)) AS score
    FROM embeddings e
    JOIN transcript_chunks c ON c.id = e.chunk_id
    JOIN transcripts t ON t.id = c.transcript_id
    ORDER BY e.embedding <=> CAST(:query_embedding AS vector)
    LIMIT :limit
    """
)

_FTS_SQL = text(
    """
    SELECT c.id AS chunk_id, c.transcript_id, c.chunk_index, c.content,
           t.title AS episode_title, t.guest, t.url,
           ts_rank_cd(to_tsvector('english', c.content), plainto_tsquery('english', :query)) AS score
    FROM transcript_chunks c
    JOIN transcripts t ON t.id = c.transcript_id
    WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', :query)
    ORDER BY score DESC
    LIMIT :limit
    """
)


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


class Retriever:
    def __init__(self, db: AsyncSession, embedder: EmbeddingProvider, settings: Settings | None = None) -> None:
        self.db = db
        self.embedder = embedder
        self.settings = settings or get_settings()

    async def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or self.settings.retrieval_top_k
        candidate_pool = max(top_k * 3, 15)

        [query_embedding] = await self.embedder.embed([query])

        vector_rows = (
            await self.db.execute(
                _VECTOR_SQL,
                {"query_embedding": _vector_literal(query_embedding), "limit": candidate_pool},
            )
        ).mappings().all()

        fts_rows = (
            await self.db.execute(_FTS_SQL, {"query": query, "limit": candidate_pool})
        ).mappings().all()

        vector_score_by_id = {str(r["chunk_id"]): r["score"] for r in vector_rows}
        lexical_ids = {str(r["chunk_id"]) for r in fts_rows}
        order = self._reciprocal_rank_fusion(vector_rows, fts_rows)

        rows_by_id = {str(r["chunk_id"]): r for r in [*vector_rows, *fts_rows]}
        candidates = [
            RetrievedChunk(
                chunk_id=cid,
                transcript_id=str(rows_by_id[cid]["transcript_id"]),
                episode_title=rows_by_id[cid]["episode_title"],
                guest=rows_by_id[cid]["guest"],
                url=rows_by_id[cid]["url"],
                chunk_index=rows_by_id[cid]["chunk_index"],
                content=rows_by_id[cid]["content"],
                score=vector_score_by_id.get(cid, 0.0),
                matched_lexically=cid in lexical_ids,
            )
            for cid in order
        ]

        supported = [
            c for c in candidates if c.score >= self.settings.retrieval_min_score or c.matched_lexically
        ]
        return supported[:top_k]

    @staticmethod
    def _reciprocal_rank_fusion(vector_rows: list, fts_rows: list, k: int = 60) -> list[str]:
        scores: dict[str, float] = {}
        for rank, row in enumerate(vector_rows):
            cid = str(row["chunk_id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        for rank, row in enumerate(fts_rows):
            cid = str(row["chunk_id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        return [cid for cid, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
