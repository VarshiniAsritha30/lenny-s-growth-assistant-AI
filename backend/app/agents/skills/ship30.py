import re
from dataclasses import dataclass

from app.agents.prompts import NO_CONTEXT_FALLBACK, SHIP30_SYSTEM, format_sources_block
from app.agents.state import ConversationTurn, build_llm_history
from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ChatMessage, LLMProvider
from app.retrieval.retriever import RetrievedChunk, Retriever

logger = get_logger(__name__)

_QUOTE_RE = re.compile(r'"([^"]{25,})"')


@dataclass
class Ship30Essay:
    title: str
    body_markdown: str
    word_count: int
    sources: list[RetrievedChunk]
    grounding_warnings: list[str]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def validate_and_repair_quotes(draft: str, chunks: list[RetrievedChunk]) -> tuple[str, list[str]]:
    """Best-effort grounding check: any long double-quoted span must appear (normalized) in the
    retrieved source material. A quote that isn't traceable is de-quoted (turned into plain
    paraphrase text, quotation marks stripped) rather than left presented as a verbatim quote we
    can't verify - the prompt already instructs the model not to fabricate quotes; this is the
    safety net for when it does anyway.
    """
    source_text = _normalize(" ".join(c.content for c in chunks))
    warnings: list[str] = []

    def repair(match: re.Match) -> str:
        quoted = match.group(1)
        if _normalize(quoted) in source_text:
            return match.group(0)
        warnings.append(f"Unverified quotation removed: \"{quoted[:60]}...\"")
        return quoted

    repaired = _QUOTE_RE.sub(repair, draft)
    return repaired, warnings


async def generate_ship30_essay(
    *,
    llm: LLMProvider,
    retriever: Retriever,
    history: list[ConversationTurn],
    topic: str,
) -> Ship30Essay:
    settings = get_settings()
    chunks = await retriever.retrieve(topic, top_k=settings.retrieval_top_k)

    if not chunks:
        return Ship30Essay(
            title=topic,
            body_markdown=NO_CONTEXT_FALLBACK,
            word_count=len(NO_CONTEXT_FALLBACK.split()),
            sources=[],
            grounding_warnings=[],
        )

    system = SHIP30_SYSTEM.format(target_words=settings.ship30_target_words)
    system += "\n\nRetrieved context:\n" + format_sources_block(chunks)

    messages = [ChatMessage(role="system", content=system), *build_llm_history(history)]
    messages.append(
        ChatMessage(
            role="user",
            content=(
                f"Write a Ship 30 for 30-style essay on: {topic}\n\n"
                "Start with a single '# Title' line, then the essay body."
            ),
        )
    )

    result = await llm.complete(messages, temperature=0.4, max_tokens=2600)
    draft = result.text.strip()

    repaired, warnings = validate_and_repair_quotes(draft, chunks)
    if warnings:
        logger.warning("ship30_grounding_warnings", warnings=warnings)

    title = topic
    body = repaired
    lines = repaired.splitlines()
    if lines and lines[0].strip().startswith("#"):
        title = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()

    word_count = len(body.split())
    return Ship30Essay(
        title=title,
        body_markdown=body,
        word_count=word_count,
        sources=chunks,
        grounding_warnings=warnings,
    )
