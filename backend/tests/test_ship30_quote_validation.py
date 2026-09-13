from app.agents.skills.ship30 import validate_and_repair_quotes
from app.retrieval.retriever import RetrievedChunk


def _chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="c1",
        transcript_id="t1",
        episode_title="Demo Episode",
        guest="Demo Guest",
        url=None,
        chunk_index=0,
        content=content,
        score=0.9,
        matched_lexically=True,
    )


def test_verified_quote_is_kept_unchanged():
    chunks = [_chunk("Activation is the single most important early metric for any product team.")]
    draft = 'The guest said "Activation is the single most important early metric for any product team."'
    repaired, warnings = validate_and_repair_quotes(draft, chunks)

    assert warnings == []
    assert '"Activation is the single most important early metric for any product team."' in repaired


def test_fabricated_quote_is_dequoted_and_flagged():
    chunks = [_chunk("We think retention curves matter more than acquisition spend.")]
    draft = 'The guest famously said "growth hacking is dead and nobody should ever do it again."'
    repaired, warnings = validate_and_repair_quotes(draft, chunks)

    assert len(warnings) == 1
    assert '"growth hacking is dead and nobody should ever do it again."' not in repaired
    assert "growth hacking is dead and nobody should ever do it again." in repaired


def test_short_quoted_fragments_are_ignored():
    chunks = [_chunk("Some unrelated source content.")]
    draft = 'This has a "short one" quote that is below the verification length threshold.'
    repaired, warnings = validate_and_repair_quotes(draft, chunks)

    assert warnings == []
    assert repaired == draft
