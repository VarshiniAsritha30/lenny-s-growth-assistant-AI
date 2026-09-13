from typing import AsyncIterator

import anthropic

from app.core.errors import ModelUnavailableError, ProviderConfigError
from app.providers.base import ChatMessage, CompletionResult, LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise ProviderConfigError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env or switch LLM_PROVIDER "
                "to 'ollama' to use the local model."
            )
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    @staticmethod
    def _split_system(messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
        system = None
        turns = []
        for m in messages:
            if m.role == "system":
                system = (system + "\n\n" + m.content) if system else m.content
            else:
                turns.append({"role": m.role, "content": m.content})
        return system, turns

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> CompletionResult:
        system, turns = self._split_system(messages)
        try:
            resp = await self._client.messages.create(
                model=self.model,
                system=system,
                messages=turns,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except anthropic.APIConnectionError as exc:
            raise ModelUnavailableError("Could not reach the Anthropic API.") from exc
        except anthropic.AuthenticationError as exc:
            raise ProviderConfigError("Anthropic API key was rejected.") from exc
        except anthropic.APIStatusError as exc:
            raise ModelUnavailableError(f"Anthropic API error: {exc.message}") from exc

        text = "".join(block.text for block in resp.content if block.type == "text")
        return CompletionResult(text=text, stop_reason=resp.stop_reason or "end_turn")

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        system, turns = self._split_system(messages)
        try:
            async with self._client.messages.stream(
                model=self.model,
                system=system,
                messages=turns,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIConnectionError as exc:
            raise ModelUnavailableError("Could not reach the Anthropic API.") from exc
        except anthropic.AuthenticationError as exc:
            raise ProviderConfigError("Anthropic API key was rejected.") from exc

    async def health_check(self) -> tuple[bool, str]:
        try:
            await self._client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True, f"Anthropic reachable, model '{self.model}' available."
        except anthropic.AuthenticationError:
            return False, "Anthropic API key was rejected."
        except anthropic.APIError as exc:
            return False, f"Anthropic API error: {exc}"
