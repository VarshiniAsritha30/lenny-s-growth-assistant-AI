import re
from enum import Enum


class Intent(str, Enum):
    GROUNDED_QA = "grounded_qa"
    SHIP30_ESSAY = "ship30_essay"
    ARTIFACT_MARKDOWN = "artifact_markdown"
    ARTIFACT_HTML = "artifact_html"


_ESSAY_ACTION_RE = re.compile(r"\b(write|draft|turn|generate|create|make)\b", re.IGNORECASE)
_ESSAY_TARGET_RE = re.compile(r"\b(essay|ship\s*30|blog post|article)\b", re.IGNORECASE)

_HTML_ARTIFACT_PATTERNS = re.compile(
    r"\b(html|web page|webpage|landing page|one[- ]?pager)\b.{0,30}\b(artifact|page|doc)?\b"
    r".*\b(html|web page|webpage)\b",
    re.IGNORECASE,
)

_MARKDOWN_ARTIFACT_PATTERNS = re.compile(
    r"\b(create|generate|make|write)\b.{0,40}\b(markdown|one[- ]?pager|summary doc|artifact|doc(ument)?)\b",
    re.IGNORECASE,
)


def classify_intent(user_message: str) -> Intent:
    """Deterministic keyword-based routing.

    A small local model cannot be trusted to reliably self-report intent via structured
    tool calls, so routing is decided in code before the LLM is invoked at all. This keeps
    behavior identical and debuggable across every provider (Ollama, Anthropic, OpenAI).
    """
    text = user_message.strip()

    if _ESSAY_TARGET_RE.search(text) and _ESSAY_ACTION_RE.search(text):
        return Intent.SHIP30_ESSAY

    if re.search(r"\bhtml\b", text, re.IGNORECASE) and re.search(
        r"\b(artifact|generate|create|make|build)\b", text, re.IGNORECASE
    ):
        return Intent.ARTIFACT_HTML

    if _MARKDOWN_ARTIFACT_PATTERNS.search(text) and re.search(
        r"\b(artifact|one[- ]?pager|doc(ument)?|markdown)\b", text, re.IGNORECASE
    ):
        return Intent.ARTIFACT_MARKDOWN

    return Intent.GROUNDED_QA
