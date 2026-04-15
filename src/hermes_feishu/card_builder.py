"""Feishu card JSON builder for Hermes Feishu plugin.

Builds Feishu interactive card JSON structures from parsed table data
and markdown content.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .table_parser import ParsedTable, TableColumn, TableCell, parse_table, split_table_and_text


def _build_table_columns(columns: List[TableColumn]) -> List[Dict[str, Any]]:
    """Build Feishu Table column definitions.

    Args:
        columns: Parsed table column definitions.

    Returns:
        List of Feishu column spec dicts.
    """
    feishu_cols: List[Dict[str, Any]] = []
    for col in columns:
        spec: Dict[str, Any] = {
            "field_type": col.field_type,
            "name": col.name,
        }
        if col.width:
            spec["width"] = col.width
        feishu_cols.append(spec)
    return feishu_cols


def _build_table_rows(
    rows: List[List[TableCell]],
    columns: List[TableColumn],
) -> List[List[Dict[str, Any]]]:
    """Build Feishu Table row data.

    Args:
        rows: Parsed table cell data.
        columns: Column definitions (for type info).

    Returns:
        List of Feishu row dicts.
    """
    feishu_rows: List[List[Dict[str, Any]]] = []
    for row in rows:
        feishu_row: List[Dict[str, Any]] = []
        for idx, cell in enumerate(row):
            col_type = "text"
            if idx < len(columns):
                col_type = columns[idx].field_type

            if col_type == "number":
                # Try to parse as number for the value field
                try:
                    cleaned = cell.text.replace(",", "").replace("%", "").strip()
                    num = float(cleaned)
                    if num == int(num):
                        num = int(num)
                    feishu_row.append({"text": cell.text, "value": num})
                except (ValueError, OverflowError):
                    feishu_row.append({"text": cell.text})
            else:
                feishu_row.append({"text": cell.text})
        feishu_rows.append(feishu_row)
    return feishu_rows


def build_table_card(
    table: ParsedTable,
    title: str = "📊 数据表格",
    template: str = "blue",
) -> Dict[str, Any]:
    """Build a Feishu interactive card containing a Table component.

    Args:
        table: A parsed table from table_parser.
        title: Card header title.
        template: Card header color template (blue, wathet, turquoise, green,
                  yellow, orange, red, carmine, violet, purple, indigo, grey).

    Returns:
        Complete Feishu card JSON dict.
    """
    columns = _build_table_columns(table.headers)
    rows = _build_table_rows(table.rows, table.headers)

    card: Dict[str, Any] = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"content": title, "tag": "plain_text"},
            "template": template,
        },
        "elements": [
            {
                "tag": "table",
                "columns": columns,
                "rows": rows,
            }
        ],
    }

    return card


def build_content_card(
    content: str,
    title: Optional[str] = None,
    template: str = "blue",
) -> Dict[str, Any]:
    """Build a Feishu card with markdown content (no table).

    Used for non-table content that should be sent as a card.

    Args:
        content: Markdown content for the card body.
        title: Optional card header title.
        template: Card header color template.

    Returns:
        Complete Feishu card JSON dict.
    """
    card: Dict[str, Any] = {
        "config": {"wide_screen_mode": True},
    }

    if title:
        card["header"] = {
            "title": {"content": title, "tag": "plain_text"},
            "template": template,
        }

    card["elements"] = [
        {
            "tag": "markdown",
            "content": content,
        }
    ]

    return card


def build_mixed_card(
    markdown: str,
    title: Optional[str] = None,
    template: str = "blue",
) -> Optional[Dict[str, Any]]:
    """Build a Feishu card that handles mixed content (text + tables).

    If the content contains tables, they are rendered as Table components.
    Non-table text is rendered as markdown elements.

    Args:
        markdown: Full markdown content that may include tables.
        title: Optional card header title.
        template: Card header color template.

    Returns:
        Complete Feishu card JSON dict, or None if no tables found
        (in which case use build_content_card or send as post message).
    """
    tables = parse_table(markdown)
    if not tables:
        return None

    card: Dict[str, Any] = {
        "config": {"wide_screen_mode": True},
    }

    if title:
        card["header"] = {
            "title": {"content": title, "tag": "plain_text"},
            "template": template,
        }

    elements: List[Dict[str, Any]] = []
    table_blocks, text_segments = split_table_and_text(markdown)

    # Interleave text and table elements in original order
    table_idx = 0
    text_idx = 0

    # Walk through the original markdown to maintain order
    import re
    _TABLE_BLOCK_RE = re.compile(
        r"((?:^\|[^\n]+\|\s*\n"
        r"^\|[\s:|-]+\|\s*\n"
        r"(?:^\|[^\n]+\|\s*\n?)*)+)",
        re.MULTILINE,
    )

    last_end = 0
    for match in _TABLE_BLOCK_RE.finditer(markdown):
        # Text before this table
        before = markdown[last_end:match.start()].strip()
        if before:
            elements.append({
                "tag": "markdown",
                "content": before,
            })

        # Table element
        if table_idx < len(tables):
            table = tables[table_idx]
            columns = _build_table_columns(table.headers)
            rows = _build_table_rows(table.rows, table.headers)
            elements.append({
                "tag": "table",
                "columns": columns,
                "rows": rows,
            })
            table_idx += 1

        last_end = match.end()

    # Remaining text after last table
    remaining = markdown[last_end:].strip()
    if remaining:
        elements.append({
            "tag": "markdown",
            "content": remaining,
        })

    card["elements"] = elements
    return card


def card_to_json(card: Dict[str, Any]) -> str:
    """Serialize a card dict to JSON string.

    Args:
        card: Feishu card JSON dict.

    Returns:
        Compact JSON string (ensure_ascii=False for CJK support).
    """
    return json.dumps(card, ensure_ascii=False, separators=(",", ":"))
