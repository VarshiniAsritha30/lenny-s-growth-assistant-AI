import re
from dataclasses import dataclass

from app.agents.prompts import ARTIFACT_HTML_SYSTEM, ARTIFACT_MARKDOWN_SYSTEM, format_sources_block
from app.agents.state import ConversationTurn, build_llm_history
from app.core.errors import ArtifactGenerationError
from app.providers.base import ChatMessage, LLMProvider
from app.retrieval.retriever import RetrievedChunk, Retriever

_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_CODE_FENCE_RE = re.compile(r"^```(?:html|markdown|md)?\s*\n(.*)\n```\s*$", re.DOTALL)


@dataclass
class GeneratedArtifact:
    type: str  # "markdown" | "html"
    title: str
    content: str
    sources: list[RetrievedChunk]


def _strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1).strip() if match else text.strip()


async def generate_artifact(
    *,
    llm: LLMProvider,
    retriever: Retriever,
    history: list[ConversationTurn],
    request: str,
    artifact_type: str,
) -> GeneratedArtifact:
    if artifact_type not in ("markdown", "html"):
        raise ArtifactGenerationError(f"Unsupported artifact type: {artifact_type}")

    chunks = await retriever.retrieve(request)
    system_template = ARTIFACT_HTML_SYSTEM if artifact_type == "html" else ARTIFACT_MARKDOWN_SYSTEM
    system = system_template + "\n\nRetrieved context:\n" + format_sources_block(chunks)

    messages = [ChatMessage(role="system", content=system), *build_llm_history(history)]
    messages.append(ChatMessage(role="user", content=request))

    result = await llm.complete(messages, temperature=0.3, max_tokens=3000)
    content = _strip_code_fence(result.text)

    if artifact_type == "html":
        content = _SCRIPT_TAG_RE.sub("", content)
        if "<html" not in content.lower():
            content = f"<!DOCTYPE html>\n<html><head><meta charset='utf-8'></head><body>{content}</body></html>"

    title = _derive_title(content, artifact_type, fallback=request[:80])
    return GeneratedArtifact(type=artifact_type, title=title, content=content, sources=chunks)


def _derive_title(content: str, artifact_type: str, fallback: str) -> str:
    if artifact_type == "markdown":
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    else:
        match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return fallback
