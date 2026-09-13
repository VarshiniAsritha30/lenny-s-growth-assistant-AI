from typing import AsyncIterator

import openai

from app.core.errors import ModelUnavailableError, ProviderConfigError
from app.providers.base import ChatMessage, CompletionResult, EmbeddingProvider, LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None, model: str) -> None:
        if not api_key:
            raise ProviderConfigError(
                "OPENAI_API_KEY is not set. Add it to your .env or switch LLM_PROVIDER "
                "to 'ollama' to use the local model."
            )
        self.model = model
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> CompletionResult:
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except openai.APIConnectionError as exc:
            raise ModelUnavailableError("Could not reach the OpenAI API.") from exc
        except openai.AuthenticationError as exc:
            raise ProviderConfigError("OpenAI API key was rejected.") from exc
        except openai.APIStatusError as exc:
            raise ModelUnavailableError(f"OpenAI API error: {exc.message}") from exc

        choice = resp.choices[0]
        return CompletionResult(text=choice.message.content or "", stop_reason=choice.finish_reason)

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.APIConnectionError as exc:
            raise ModelUnavailableError("Could not reach the OpenAI API.") from exc
        except openai.AuthenticationError as exc:
            raise ProviderConfigError("OpenAI API key was rejected.") from exc

    async def health_check(self) -> tuple[bool, str]:
        try:
            await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True, f"OpenAI reachable, model '{self.model}' available."
        except openai.AuthenticationError:
            return False, "OpenAI API key was rejected."
        except openai.APIError as exc:
            return False, f"OpenAI API error: {exc}"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(self, api_key: str | None, model: str, dimensions: int) -> None:
        if not api_key:
            raise ProviderConfigError("OPENAI_API_KEY is not set.")
        self.model = model
        self.dimensions = dimensions
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = await self._client.embeddings.create(model=self.model, input=texts)
        except openai.APIConnectionError as exc:
            raise ModelUnavailableError("Could not reach the OpenAI API.") from exc
        except openai.AuthenticationError as exc:
            raise ProviderConfigError("OpenAI API key was rejected.") from exc
        return [d.embedding for d in resp.data]

    async def health_check(self) -> tuple[bool, str]:
        try:
            await self._client.embeddings.create(model=self.model, input=["ping"])
            return True, f"OpenAI reachable, embedding model '{self.model}' available."
        except openai.AuthenticationError:
            return False, "OpenAI API key was rejected."
        except openai.APIError as exc:
            return False, f"OpenAI API error: {exc}"
