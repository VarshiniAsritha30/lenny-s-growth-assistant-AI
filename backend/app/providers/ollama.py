from typing import AsyncIterator

import httpx

from app.core.errors import ModelUnavailableError
from app.providers.base import ChatMessage, CompletionResult, EmbeddingProvider, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._timeout = timeout

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> CompletionResult:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                "Local model unavailable. Start Ollama and verify the configured model "
                f"('{self.model}') is pulled (ollama pull {self.model})."
            ) from exc
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama timed out generating a response for model '{self.model}'."
            ) from exc

        if resp.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{self.model}' is not pulled in Ollama. Run: ollama pull {self.model}"
            )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        return CompletionResult(text=text, stop_reason=data.get("done_reason", "end_turn"))

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    if resp.status_code == 404:
                        raise ModelUnavailableError(
                            f"Model '{self.model}' is not pulled in Ollama. "
                            f"Run: ollama pull {self.model}"
                        )
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        import json

                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            break
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                "Local model unavailable. Start Ollama and verify the configured model "
                f"('{self.model}') is pulled (ollama pull {self.model})."
            ) from exc

    async def health_check(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                if not any(self.model in m for m in models):
                    return False, f"Ollama is running but model '{self.model}' is not pulled."
                return True, f"Ollama reachable, model '{self.model}' available."
        except httpx.HTTPError:
            return False, "Ollama is not reachable at " + self.base_url


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, dimensions: int, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self._timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for text in texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                    )
                    if resp.status_code == 404:
                        raise ModelUnavailableError(
                            f"Embedding model '{self.model}' is not pulled in Ollama. "
                            f"Run: ollama pull {self.model}"
                        )
                    resp.raise_for_status()
                    results.append(resp.json()["embedding"])
        except httpx.ConnectError as exc:
            raise ModelUnavailableError(
                "Local model unavailable. Start Ollama and verify the configured embedding "
                f"model ('{self.model}') is pulled (ollama pull {self.model})."
            ) from exc
        return results

    async def health_check(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                if not any(self.model in m for m in models):
                    return False, f"Ollama is running but embedding model '{self.model}' is not pulled."
                return True, f"Ollama reachable, embedding model '{self.model}' available."
        except httpx.HTTPError:
            return False, "Ollama is not reachable at " + self.base_url
