import re
from dataclasses import dataclass

from app.agents.prompts import (
    EMPTY_HISTORY_NOTE,
    GROUNDED_QA_SYSTEM,
    NO_CONTEXT_FALLBACK,
    format_sources_block,
)
from app.agents.state import ConversationTurn, build_llm_history, build_retrieval_query
from app.providers.base import ChatMessage, LLMProvider
from app.retrieval.retriever import RetrievedChunk, Retriever


@dataclass
class GroundedAnswer:
    text: str
    sources: list[RetrievedChunk]
    is_grounded: bool  # False when retrieval found nothing supportable - fallback text is used


_META_RECAP_RE = re.compile(
    r"\b(what (were|did|have) we (just )?(talk(ing)?|discuss(ing)?|chat(ting)?)"
    r"|what (did|have) (you|i) (say|said|tell|told)"
    r"|(summarize|recap) (our|this|the) conversation)\b",
    re.IGNORECASE,
)

NEW_CONVERSATION_RECAP = (
    "This is a new conversation — there's no earlier history in this session to recap yet. "
    "Ask me a product or growth question and I'll get started."
)


async def answer_grounded_question(
    *,
    llm: LLMProvider,
    retriever: Retriever,
    history: list[ConversationTurn],
    question: str,
) -> GroundedAnswer:
    # Deterministic guard, not left to the LLM: a small local model will reliably conflate
    # "Retrieved context" (transcript excerpts) with actual prior chat turns when asked to recap
    # a conversation that never happened, which reads exactly like a session-isolation leak even
    # though the underlying data is correctly scoped. Short-circuit this specific, testable
    # failure mode rather than relying on prompt instructions a 1B-parameter model won't reliably
    # follow (see docs/IMPLEMENTATION_PLAN.md / README known limitations).
    if not history and _META_RECAP_RE.search(question):
        return GroundedAnswer(text=NEW_CONVERSATION_RECAP, sources=[], is_grounded=True)

    retrieval_query = build_retrieval_query(history, question)
    chunks = await retriever.retrieve(retrieval_query)

    if not chunks:
        return GroundedAnswer(text=NO_CONTEXT_FALLBACK, sources=[], is_grounded=False)

    system = GROUNDED_QA_SYSTEM
    if not history:
        system += EMPTY_HISTORY_NOTE
    system += "\n\nRetrieved context:\n" + format_sources_block(chunks)
    messages = [ChatMessage(role="system", content=system), *build_llm_history(history)]
    messages.append(ChatMessage(role="user", content=question))

    result = await llm.complete(messages, temperature=0.2, max_tokens=900)
    return GroundedAnswer(text=result.text, sources=chunks, is_grounded=True)
