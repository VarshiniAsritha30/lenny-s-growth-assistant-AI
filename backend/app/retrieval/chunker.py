import re
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int


_WORD_RE = re.compile(r"\S+")


def _approx_tokens(text: str) -> int:
    # ~0.75 tokens/word is a reasonable approximation without pulling in a tokenizer
    # dependency purely for chunk sizing.
    return int(len(_WORD_RE.findall(text)) / 0.75)


def chunk_text(
    content: str,
    *,
    target_tokens: int = 350,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Paragraph-aware sliding-window chunking.

    Splits on paragraph boundaries first (so a chunk doesn't cut a sentence in half unless a
    single paragraph itself exceeds the target size), then packs paragraphs into ~target_tokens
    windows with a small overlap so context isn't lost at chunk edges.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if current:
            text = "\n\n".join(current)
            chunks.append(Chunk(index=len(chunks), content=text, token_count=_approx_tokens(text)))
        current, current_tokens = [], 0

    for para in paragraphs:
        para_tokens = _approx_tokens(para)

        if para_tokens > target_tokens * 1.5:
            flush()
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf, buf_tokens = [], 0
            for sent in sentences:
                sent_tokens = _approx_tokens(sent)
                if buf and buf_tokens + sent_tokens > target_tokens:
                    text = " ".join(buf)
                    chunks.append(Chunk(index=len(chunks), content=text, token_count=_approx_tokens(text)))
                    buf, buf_tokens = [], 0
                buf.append(sent)
                buf_tokens += sent_tokens
            if buf:
                text = " ".join(buf)
                chunks.append(Chunk(index=len(chunks), content=text, token_count=_approx_tokens(text)))
            continue

        if current and current_tokens + para_tokens > target_tokens:
            flush()
            if overlap_tokens and chunks:
                tail_words = chunks[-1].content.split()
                overlap_word_count = int(overlap_tokens * 0.75)
                overlap_text = " ".join(tail_words[-overlap_word_count:])
                if overlap_text:
                    current = [overlap_text]
                    current_tokens = _approx_tokens(overlap_text)

        current.append(para)
        current_tokens += para_tokens

    flush()

    for i, c in enumerate(chunks):
        c.index = i
    return chunks
