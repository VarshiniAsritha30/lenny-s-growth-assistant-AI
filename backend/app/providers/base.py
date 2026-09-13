from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionResult:
    text: str
    stop_reason: str = "end_turn"


class LLMProvider(ABC):
    """Common interface every chat-model backend implements.

    Application code (the agent orchestrator, skills, routes) only ever talks to this
    interface - never to a concrete provider - so switching LLM_PROVIDER is a config
    change, not a code change. Routing/tool-selection is done deterministically in
    app/agents/router.py rather than via model-driven tool calling, because the mandatory
    local demo model (a small Ollama model) cannot be relied on to emit structured tool
    calls reliably.
    """

    name: str
    model: str

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> CompletionResult: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Returns (is_healthy, human_readable_detail)."""
        ...


class EmbeddingProvider(ABC):
    name: str
    dimensions: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]: ...
