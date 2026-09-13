import os
from collections.abc import AsyncIterator
from typing import AsyncIterator as AsyncIteratorType

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:lenny_dev_password@127.0.0.1:5544/lenny_growth_assistant_test",
)
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("EMBEDDING_PROVIDER", "ollama")

from app.api.deps import get_embedding_provider, get_llm_provider  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.base import ChatMessage, CompletionResult, EmbeddingProvider, LLMProvider  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


class FakeLLMProvider(LLMProvider):
    """Deterministic stand-in for a real model - keeps most tests fast and offline while still
    exercising the full orchestrator/skill/route stack.
    """

    name = "fake"
    model = "fake-model"

    def __init__(self, response: str = "This is a fake grounded answer citing Source 1.") -> None:
        self._response = response
        self.calls: list[list[ChatMessage]] = []

    async def complete(self, messages, *, temperature=0.3, max_tokens=2000) -> CompletionResult:
        self.calls.append(messages)
        return CompletionResult(text=self._response)

    async def stream(self, messages, *, temperature=0.3, max_tokens=2000):
        yield self._response

    async def health_check(self) -> tuple[bool, str]:
        return True, "fake provider always healthy"


class RefusingLLMProvider(FakeLLMProvider):
    """Used to prove a code path never calls the LLM at all (e.g. the empty-history recap guard)."""

    async def complete(self, messages, *, temperature=0.3, max_tokens=2000):
        raise AssertionError("LLM should not have been called")


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"
    dimensions = 768

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]

    async def health_check(self) -> tuple[bool, str]:
        return True, "fake embedder always healthy"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _prepare_test_database() -> AsyncIteratorType[None]:
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]

    async with admin_engine.connect() as conn:
        from sqlalchemy import text

        exists = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name})
        if not exists.scalar():
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await admin_engine.dispose()

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    yield


@pytest_asyncio.fixture
async def db_session(_prepare_test_database) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async with session_maker() as session:
        yield session

    # Truncate rather than drop/recreate between tests - much faster, and every table needs
    # resetting since tests share the schema across the session-scoped database fixture.
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(
            text(
                "TRUNCATE artifacts, messages, sessions, embeddings, transcript_chunks, "
                "transcripts, users RESTART IDENTITY CASCADE"
            )
        )
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def fake_embedder() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def override_llm():
    """Call with a provider instance to make routes use it for the duration of the test."""

    def _override(provider: LLMProvider) -> None:
        app.dependency_overrides[get_llm_provider] = lambda: provider

    yield _override
    app.dependency_overrides.pop(get_llm_provider, None)


@pytest.fixture
def override_embedder():
    def _override(provider: EmbeddingProvider) -> None:
        app.dependency_overrides[get_embedding_provider] = lambda: provider

    yield _override
    app.dependency_overrides.pop(get_embedding_provider, None)


def _ollama_available_sync() -> bool:
    import httpx

    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any("llama3.2:1b" in m for m in models) and any("nomic-embed-text" in m for m in models)
    except Exception:  # noqa: BLE001
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_available_sync(),
    reason="Requires a local Ollama daemon with llama3.2:1b and nomic-embed-text pulled",
)
