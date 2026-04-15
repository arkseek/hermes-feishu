"""Hermes Feishu Plugin - Enhanced Feishu messaging with card messages and table rendering.

This plugin enhances Hermes Agent's Feishu messaging capabilities by providing:
- send_feishu_card: Send rich card messages with table support
- send_feishu_table: Send structured tables as card messages
- pre_llm_call hook: Auto-inject formatting instructions for Feishu platform
"""

import logging

from .schemas import SEND_FEISHU_CARD_SCHEMA, SEND_FEISHU_TABLE_SCHEMA
from .sender import _has_credentials
from .tools import send_feishu_card, send_feishu_table

__version__ = "0.3.6"

logger = logging.getLogger("hermes-feishu")


def register(ctx):
    """Register plugin tools and hooks with Hermes Agent.

    Args:
        ctx: Plugin registration context provided by Hermes.
    """
    # Register tools with conditional availability
    ctx.register_tool(
        name="send_feishu_card",
        toolset="feishu",
        schema=SEND_FEISHU_CARD_SCHEMA,
        handler=send_feishu_card,
        check_fn=_has_credentials,
    )

    ctx.register_tool(
        name="send_feishu_table",
        toolset="feishu",
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
    chat_id: str = "",
    sender_id: str = "",
    **kwargs,
):
    """Inject Feishu formatting instructions when platform is Feishu.

    Injects on every turn to ensure LLM remembers to use card tools.
    Uses full instructions on first turn, brief reminder on subsequent turns.
    Also provides the current chat_id so LLM can call tools without guessing.

    Args:
        session_id: Current session ID.
        user_message: The user's message.
        conversation_history: Conversation history.
        is_first_turn: Whether this is the first turn.
        model: Model name.
        platform: Platform identifier (e.g., 'feishu').
        chat_id: Current chat/channel ID.
        sender_id: Sender user ID.

    Returns:
        Context dict to inject, or None.
    """
    # Normalize platform name (case-insensitive check)
    if not platform or platform.lower() not in ("feishu", "lark"):
        return None

    # Store chat_id in os.environ for tools to access
    # (contextvars don't propagate across thread pool boundary)
    import os
    if chat_id:
        os.environ["HERMES_SESSION_CHAT_ID"] = chat_id

    # Log hook activation for debugging
    logger.info(
        f"[hermes-feishu] pre_llm_call hook: platform={platform}, chat_id={chat_id or '(empty)'}, session_id={session_id}, sender_id={sender_id or '(empty)'}"
    )
    # Debug: print all kwargs to see what Hermes passes
    if kwargs:
        logger.info(f"[hermes-feishu] pre_llm_call kwargs keys: {list(kwargs.keys())}, values: {kwargs}")
    else:
        logger.info("[hermes-feishu] pre_llm_call kwargs is empty")

    # Hermes doesn't pass chat_id and contextvars don't propagate to thread pool.
    # Extract chat_id from session_id format: "agent:main:feishu:dm:oc_xxx"
    if not chat_id and session_id:
        # session_id format: "agent:main:<platform>:<chat_type>:<chat_id>[:thread_id]"
        # or "agent:main:<platform>:<chat_type>" (if chat_id missing)
        parts = session_id.split(":")
        if len(parts) >= 5:
            # chat_id is at index 4 (after agent:main:platform:chat_type)
            potential_chat_id = parts[4]
            if potential_chat_id.startswith(("oc_", "ou_", "gc_")):  # Feishu chat ID prefixes
                chat_id = potential_chat_id
                logger.info(f"[hermes-feishu] Extracted chat_id from session_id: {chat_id}")

    # Build context with chat_id - inject on EVERY turn to ensure LLM remembers
    context = (
        "\n\n[System: Feishu Platform Instructions]\n"
        "You are connected via Feishu (飞书). Feishu messages have limited Markdown support:\n"
        "- ✅ Supported: bold, italic, lists, code blocks, headers\n"
        "- ❌ NOT supported: Markdown tables\n\n"
        "**IMPORTANT**: When your response contains tabular data:\n"
        "1. Use `send_feishu_card` or `send_feishu_table` tool to render tables\n"
        "2. Do NOT include Markdown table syntax in your regular text response\n"
        "3. You can still use other Markdown formatting in normal messages\n\n"
        "**Reaction Feature**: Messages sent via tools will automatically get a DONE (✅) reaction.\n"
        "This indicates successful completion. No need to specify reaction parameter.\n"
    )
    
    if chat_id:
        context += f"\n**Current chat_id**: `{chat_id}`\n"
        logger.info(f"[hermes-feishu] Injected chat_id into context: {chat_id}")
    
    # Log injection for debugging
    logger.debug(f"[hermes-feishu] Injecting context (length={len(context)} chars)")
    
    return {"context": context}
