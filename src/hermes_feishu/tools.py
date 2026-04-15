"""Tool handlers for Hermes Feishu plugin.

Implements the send_feishu_card and send_feishu_table tool handlers
that the LLM calls to send rich card messages to Feishu.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from .card_builder import build_mixed_card, build_table_card
from .schemas import SEND_FEISHU_CARD_SCHEMA, SEND_FEISHU_TABLE_SCHEMA
from .sender import _has_credentials, send_card
from .table_parser import ParsedTable, TableColumn, TableCell

logger = logging.getLogger(__name__)


def send_feishu_card(args: dict, **kwargs) -> str:
    """Send a Feishu card with Markdown content (may include tables).

    Tool handler for the LLM. Accepts Markdown content and sends it as
    a Feishu interactive card. Tables in the content are automatically
    converted to Feishu Table components.

    Args:
        args: Tool arguments dict with keys: content, title (optional),
              chat_id (optional), template (optional).
        **kwargs: Additional context (may include chat_id from session).

    Returns:
        JSON string with result.
    """
    content = args.get("content", "")
    title = args.get("title", "")
    chat_id = args.get("chat_id", "") or kwargs.get("chat_id", "")
    template = args.get("template", "blue")

    if not content:
        return json.dumps({"error": "No content provided"})

    if not chat_id:
        return json.dumps({"error": "No chat_id provided. Cannot determine target chat."})

    # Check for tables in content
    from .table_parser import parse_table, contains_table

    if contains_table(content):
        tables = parse_table(content)
        if tables:
            if not title:
                title = "📊 数据表格"
            card = build_mixed_card(content, title=title, template=template)
            if card is None:
                from .card_builder import build_content_card
                card = build_content_card(content, title=title, template=template)
        else:
            from .card_builder import build_content_card
            card = build_content_card(content, title=title or None, template=template)
    else:
        from .card_builder import build_content_card
        card = build_content_card(
            content,
            title=title or None,
            template=template,
        )

    result = send_card(card, chat_id)
    return result


def send_feishu_table(args: dict, **kwargs) -> str:
    """Send a structured table as a Feishu card.

    Tool handler for the LLM. Accepts structured headers and rows data
    and sends it as a Feishu card with a Table component.

    Args:
        args: Tool arguments dict with keys: headers (list of str),
              rows (list of list of str), title (optional), chat_id (optional),
              template (optional).
        **kwargs: Additional context (may include chat_id from session).

    Returns:
        JSON string with result.
    """
    headers_raw = args.get("headers", [])
    rows_raw = args.get("rows", [])
    title = args.get("title", "") or "📊 数据表格"
    chat_id = args.get("chat_id", "") or kwargs.get("chat_id", "")
    template = args.get("template", "blue")

    if not headers_raw:
        return json.dumps({"error": "No headers provided"})

    if not rows_raw:
        return json.dumps({"error": "No rows provided"})

    if not chat_id:
        return json.dumps({"error": "No chat_id provided. Cannot determine target chat."})

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

    result = send_card(card, chat_id)
    return result
