"""Tool handlers for Hermes Feishu plugin.

Implements the send_feishu_card and send_feishu_table tool handlers
that the LLM calls to send rich card messages to Feishu.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, List

from .card_builder import build_content_card, build_mixed_card, build_table_card
from .schemas import SEND_FEISHU_CARD_SCHEMA, SEND_FEISHU_TABLE_SCHEMA
from .sender import _has_credentials, send_card
from .table_parser import ParsedTable, TableColumn, TableCell

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Thread-local session context
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def set_session_chat_id(chat_id: str) -> None:
    """Store chat_id in thread-local storage for tool handlers.

    Called by the pre_llm_call hook. Safe within the same thread.
    Falls back to os.environ for cross-thread scenarios (see _get_session_chat_id).
    """
    if chat_id:
        _thread_local.chat_id = chat_id


# ---------------------------------------------------------------------------
# Session context helpers
# ---------------------------------------------------------------------------

def _get_session_chat_id() -> str:
    """Get chat_id from Hermes session context.

    Resolution order:
    1. Thread-local storage (set by pre_llm_call hook, safe within same thread)
    2. gateway.session_context.get_session_env (contextvars)
    3. os.environ["HERMES_SESSION_CHAT_ID"] (fallback, has race condition for concurrent sessions)
    """
    # Try thread-local first (safe within same thread)
    chat_id = getattr(_thread_local, "chat_id", "")
    if chat_id:
        logger.debug(f"Got chat_id from thread-local: {chat_id}")
        return chat_id

    # Try contextvars (Hermes gateway)
    try:
        from gateway.session_context import get_session_env  # type: ignore[import-untyped]
        chat_id = get_session_env("HERMES_SESSION_CHAT_ID", "")
        if chat_id:
            logger.debug(f"Got chat_id from contextvars: {chat_id}")
            return chat_id
        else:
            logger.debug("contextvars returned empty, checking os.environ fallback")
    except ImportError as e:
        logger.debug(f"Cannot import gateway.session_context: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error getting session context: {e}")

    # Fallback: os.environ (known race condition for concurrent sessions)
    env_chat_id = os.environ.get("HERMES_SESSION_CHAT_ID", "")
    if env_chat_id:
        logger.debug(f"Got chat_id from os.environ: {env_chat_id}")
    else:
        logger.warning("No chat_id found in thread-local, contextvars, or os.environ")
    return env_chat_id


def _resolve_chat_id(args: dict, **kwargs) -> str:
    """Resolve chat_id from multiple sources with priority.

    Priority:
    1. args["chat_id"] — LLM explicitly passed
    2. kwargs["chat_id"] — Hermes dispatcher kwargs (currently unused)
    3. Hermes session context (thread-local / contextvars / os.environ)
    4. HERMES_FEISHU_CHAT_ID from os.environ (fallback for single-chat scenarios)
    """
    chat_id = (
        args.get("chat_id", "")
        or kwargs.get("chat_id", "")
        or _get_session_chat_id()
        or os.environ.get("HERMES_FEISHU_CHAT_ID", "")
    )

    if not chat_id:
        logger.error("No chat_id available from any source (args, kwargs, session, or default)")

    return chat_id


def send_feishu_card(args: dict, **kwargs) -> str:
    """Send a Feishu card with Markdown content (may include tables).

    Tool handler for the LLM. Accepts Markdown content and sends it as
    a Feishu interactive card. Tables in the content are automatically
    converted to Feishu Table components.

    Args:
        args: Tool arguments dict with keys: content, title (optional),
              chat_id (optional), template (optional), reaction (optional).
        **kwargs: Additional context (may include chat_id from session).

    Returns:
        JSON string with result.
    """
    content = args.get("content", "")
    title = args.get("title", "")
    chat_id = _resolve_chat_id(args, **kwargs)
    template = args.get("template", "blue")
    reaction = args.get("reaction") or "DONE"  # Default: "DONE" (✅ completed)
    # Set to empty string to skip reaction

    if not content:
        return json.dumps({"error": "No content provided"})

    if not chat_id:
        error_msg = {
            "error": "无法确定目标会话 (chat_id)",
            "hint": "Hermes 未传递 chat_id 给插件",
            "solutions": [
                "方法 1: 在 ~/.hermes/.env 中添加 HERMES_FEISHU_CHAT_ID=oc_xxx (推荐单会话使用)",
                "方法 2: 工具调用时显式指定 chat_id 参数",
                "方法 3: 向 Hermes 提交 Issue 请求传递 chat_id 给插件"
            ]
        }
        logger.error(f"No chat_id resolved: {error_msg}")
        return json.dumps(error_msg, ensure_ascii=False)

    # Check for tables in content
    from .table_parser import parse_table, contains_table

    if contains_table(content):
        tables = parse_table(content)
        if tables:
            if not title:
                title = "📊 数据表格"
            card = build_mixed_card(content, title=title, template=template)
            if card is None:
                card = build_content_card(content, title=title, template=template)
        else:
            card = build_content_card(content, title=title or None, template=template)
    else:
        card = build_content_card(
            content,
            title=title or None,
            template=template,
        )

    result = send_card(card, chat_id, add_reaction=reaction)
    return result


def send_feishu_table(args: dict, **kwargs) -> str:
    """Send a structured table as a Feishu card.

    Tool handler for the LLM. Accepts structured headers and rows data
    and sends it as a Feishu card with a Table component.

    Args:
        args: Tool arguments dict with keys: headers (list of str),
              rows (list of list of str), title (optional), chat_id (optional),
              template (optional), reaction (optional).
        **kwargs: Additional context (may include chat_id from session).

    Returns:
        JSON string with result.
    """
    headers_raw = args.get("headers", [])
    rows_raw = args.get("rows", [])
    title = args.get("title", "") or "📊 数据表格"
    chat_id = _resolve_chat_id(args, **kwargs)
    template = args.get("template", "blue")
    reaction = args.get("reaction") or "DONE"  # Default: "DONE" (✅ completed)
    # Set to empty string to skip reaction

    if not headers_raw:
        return json.dumps({"error": "No headers provided"})

    if not rows_raw:
        return json.dumps({"error": "No rows provided"})

    if not chat_id:
        error_msg = {
            "error": "无法确定目标会话 (chat_id)",
            "hint": "Hermes 未传递 chat_id 给插件",
            "solutions": [
                "方法 1: 在 ~/.hermes/.env 中添加 HERMES_FEISHU_CHAT_ID=oc_xxx (推荐单会话使用)",
                "方法 2: 工具调用时显式指定 chat_id 参数",
                "方法 3: 向 Hermes 提交 Issue 请求传递 chat_id 给插件"
            ]
        }
        logger.error(f"No chat_id resolved: {error_msg}")
        return json.dumps(error_msg, ensure_ascii=False)

    # Convert headers and rows to ParsedTable
    columns = [
        TableColumn(name=str(h), index=i)
        for i, h in enumerate(headers_raw)
    ]

    rows: List[List[TableCell]] = []
    all_values: Dict[int, List[str]] = {col.index: [] for col in columns}

    for row_data in rows_raw:
        cells: List[TableCell] = []
        for idx, val in enumerate(row_data):
            val_str = str(val)
            if idx < len(columns):
                tc = TableCell(text=val_str)
                cells.append(tc)
                all_values[idx].append(val_str)
            else:
                cells.append(TableCell(text=val_str))
        rows.append(cells)

    # Infer column types
    from .table_parser import _infer_column_type
    for col in columns:
        col.field_type = _infer_column_type(all_values.get(col.index, []))

    parsed = ParsedTable(headers=columns, rows=rows)
    card = build_table_card(parsed, title=title, template=template)

    result = send_card(card, chat_id, add_reaction=reaction)
    return result
