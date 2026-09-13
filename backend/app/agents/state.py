from dataclasses import dataclass

from app.providers.base import ChatMessage

MAX_HISTORY_TURNS = 8


@dataclass
class ConversationTurn:
    role: str
    content: str


def build_llm_history(turns: list[ConversationTurn]) -> list[ChatMessage]:
    """Caps history so context stays bounded; each session's turns are already isolated by
    session_id at the persistence layer, so a new chat never sees another session's turns.
    """
    recent = turns[-MAX_HISTORY_TURNS:]
    return [ChatMessage(role=t.role, content=t.content) for t in recent]


def build_retrieval_query(turns: list[ConversationTurn], current_message: str) -> str:
    """Conversation-aware query transformation for retrieval.

    Follow-up questions ("What about retention?") often lack the noun phrase needed for a good
    embedding match on their own. Folding in the previous user turn gives the embedding model
    the missing context without requiring an extra LLM call (which would add latency and another
    failure mode on the mandatory local-model path).
    """
    previous_user_turns = [t.content for t in turns if t.role == "user"]
    if not previous_user_turns:
        return current_message
    last_user_turn = previous_user_turns[-1]
    if last_user_turn.strip() == current_message.strip():
        return current_message
    return f"{last_user_turn}\n{current_message}"
