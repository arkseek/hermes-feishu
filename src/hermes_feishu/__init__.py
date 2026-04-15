"""Hermes Feishu Plugin - Enhanced Feishu messaging with card messages and table rendering.

This plugin enhances Hermes Agent's Feishu messaging capabilities by providing:
- send_feishu_card: Send rich card messages with table support
- send_feishu_table: Send structured tables as card messages
- pre_llm_call hook: Auto-inject formatting instructions for Feishu platform
"""

from .schemas import SEND_FEISHU_CARD_SCHEMA, SEND_FEISHU_TABLE_SCHEMA
from .sender import _has_credentials
from .tools import send_feishu_card, send_feishu_table

__version__ = "0.2.0"

# Context injection for Feishu platform
_FEISHU_CONTEXT_INJECTION = (
    "\n\n[System: Feishu Platform Formatting]\n"
    "You are connected via Feishu (Lark). Feishu post messages do NOT support "
    "Markdown table syntax. When your response contains tabular data, you MUST "
    "use the `send_feishu_card` or `send_feishu_table` tool to render it properly.\n"
    "- Use `send_feishu_card` for Markdown content that includes tables.\n"
    "- Use `send_feishu_table` for structured data (headers + rows).\n"
    "- Do NOT include Markdown tables in your regular text response.\n"
    "- Other Markdown (bold, italic, lists, code blocks) works fine in normal messages.\n"
)


def register(ctx):
    """Register plugin tools and hooks with Hermes Agent.

    Args:
        ctx: Plugin registration context provided by Hermes.
    """
    # Register tools with conditional availability
    ctx.register_tool(
        name="send_feishu_card",
        schema=SEND_FEISHU_CARD_SCHEMA,
        handler=send_feishu_card,
        check_fn=_has_credentials,
    )

    ctx.register_tool(
        name="send_feishu_table",
        schema=SEND_FEISHU_TABLE_SCHEMA,
        handler=send_feishu_table,
        check_fn=_has_credentials,
    )

    # Register pre_llm_call hook for Feishu context injection
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)


def _on_pre_llm_call(
    session_id: str = "",
    user_message: str = "",
    conversation_history=None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs,
):
    """Inject Feishu formatting instructions when platform is Feishu.

    Only injects on the first turn of a session to avoid repetition,
    and only when the platform is 'feishu'.

    Args:
        session_id: Current session ID.
        user_message: The user's message.
        conversation_history: Conversation history.
        is_first_turn: Whether this is the first turn.
        model: Model name.
        platform: Platform identifier (e.g., 'feishu').

    Returns:
        Context dict to inject, or None.
    """
    if not is_first_turn:
        return None

    # Normalize platform name (case-insensitive check)
    if not platform or platform.lower() not in ("feishu", "lark"):
        return None

    return {"context": _FEISHU_CONTEXT_INJECTION}
