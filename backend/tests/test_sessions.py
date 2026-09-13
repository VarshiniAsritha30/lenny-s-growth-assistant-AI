import uuid

import pytest

from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider, RefusingLLMProvider


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_and_get_session(client):
    resp = await client.post("/api/sessions", json={"title": "My session"})
    assert resp.status_code == 201
    session = resp.json()
    assert session["title"] == "My session"

    resp = await client.get(f"/api/sessions/{session['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session["id"]


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_structured_404(client):
    resp = await client.get(f"/api/sessions/{uuid.uuid4()}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_invalid_message_body_returns_422_structured_error(client):
    resp = await client.post("/api/sessions", json={})
    session_id = resp.json()["id"]

    resp = await client.post(f"/api/sessions/{session_id}/messages", json={"content": ""})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_delete_session_removes_it_and_its_messages(client, override_llm, override_embedder):
    override_llm(FakeLLMProvider())
    override_embedder(FakeEmbeddingProvider())

    resp = await client.post("/api/sessions", json={})
    session_id = resp.json()["id"]
    await client.post(f"/api/sessions/{session_id}/messages", json={"content": "hello"})

    resp = await client.delete(f"/api/sessions/{session_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_new_session_never_sees_another_sessions_messages(client, override_llm, override_embedder):
    override_llm(FakeLLMProvider(response="Answer grounded in Source 1."))
    override_embedder(FakeEmbeddingProvider())

    s1 = (await client.post("/api/sessions", json={"title": "First"})).json()["id"]
    s2 = (await client.post("/api/sessions", json={"title": "Second"})).json()["id"]

    await client.post(f"/api/sessions/{s1}/messages", json={"content": "Tell me about pricing strategy"})

    s1_messages = (await client.get(f"/api/sessions/{s1}/messages")).json()
    s2_messages = (await client.get(f"/api/sessions/{s2}/messages")).json()

    assert len(s1_messages) == 2  # user + assistant
    assert len(s2_messages) == 0


@pytest.mark.asyncio
async def test_meta_recap_on_fresh_session_never_calls_the_llm(client, override_llm, override_embedder):
    """Regression test: a small local model will confuse retrieved transcript excerpts with
    actual prior chat turns when asked to recap a conversation that never happened, producing an
    answer that looks exactly like a session-isolation leak. The deterministic guard in
    grounded_qa.py must short-circuit before the LLM is ever invoked.
    """
    override_llm(RefusingLLMProvider())
    override_embedder(FakeEmbeddingProvider())

    session_id = (await client.post("/api/sessions", json={})).json()["id"]
    resp = await client.post(
        f"/api/sessions/{session_id}/messages", json={"content": "What were we just talking about?"}
    )

    assert resp.status_code == 201
    body = resp.json()
    assert "new conversation" in body["assistant_message"]["content"].lower()
    assert body["sources"] == []
