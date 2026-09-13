"""Runtime-mutable provider selection.

LLM_PROVIDER in the environment sets the *default* at startup, but POST /api/models/select
lets an operator switch providers at runtime without restarting the process or touching code -
this module is the single mutable piece of state that makes that possible.
"""

_active_provider: str | None = None


def get_active_provider_name(default: str) -> str:
    return _active_provider or default


def set_active_provider_name(name: str) -> None:
    global _active_provider
    _active_provider = name
