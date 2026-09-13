from app.retrieval.chunker import chunk_text


def test_empty_content_returns_no_chunks():
    assert chunk_text("") == []


def test_short_content_is_a_single_chunk():
    chunks = chunk_text("Paragraph one.\n\nParagraph two.")
    assert len(chunks) == 1
    assert "Paragraph one." in chunks[0].content
    assert "Paragraph two." in chunks[0].content


def test_long_content_splits_into_multiple_chunks_with_sequential_index():
    paragraph = " ".join([f"Sentence number {i} about growth strategy." for i in range(80)])
    content = "\n\n".join([paragraph] * 4)
    chunks = chunk_text(content, target_tokens=100, overlap_tokens=20)

    assert len(chunks) > 1
    assert [c.index for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert c.token_count > 0


def test_overlap_preserves_context_between_adjacent_chunks():
    paragraphs = [f"This is paragraph {i} with some unique filler content about product growth." for i in range(20)]
    content = "\n\n".join(paragraphs)
    chunks = chunk_text(content, target_tokens=40, overlap_tokens=15)

    assert len(chunks) > 2
    tail_of_first = chunks[0].content.split()[-5:]
    assert any(word in chunks[1].content for word in tail_of_first)
