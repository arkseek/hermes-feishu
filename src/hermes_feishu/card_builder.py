"""Feishu card JSON builder for Hermes Feishu plugin.

Builds Feishu interactive card JSON structures from parsed table data
and markdown content.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .table_parser import (
    ParsedTable,
    TableColumn,
    TableCell,
    _BLANK_LINE_RE,
    _TABLE_BLOCK_RE,
    parse_table,
)


def _build_table_columns(columns: List[TableColumn]) -> List[Dict[str, Any]]:
    """Build Feishu Table column definitions.

    Args:
        columns: Parsed table column definitions.

    Returns:
        List of Feishu column spec dicts.

    Feishu column format:
        {"name": "field_name", "display_name": "显示名称", "width": "auto", "field_type": "text|number"}
    """
    feishu_cols: List[Dict[str, Any]] = []
    for idx, col in enumerate(columns):
        spec: Dict[str, Any] = {
            "name": f"col_{idx}",  # Internal field key for row mapping
            "display_name": col.name,  # Column header text shown in UI
            "width": "auto",
            "field_type": col.field_type or "text",  # Use inferred type
        }
        if col.width:
            spec["width"] = col.width
        feishu_cols.append(spec)
    return feishu_cols


def _convert_cell_value(cell: TableCell, field_type: str) -> Any:
    """Convert cell text to the appropriate type based on column field_type.

    For number columns, attempt numeric conversion so Feishu renders proper
    alignment. Falls back to string if conversion fails.

    Args:
        cell: Parsed table cell.
        field_type: Column field type ("text" or "number").

    Returns:
        String for text columns, int/float for number columns (if convertible).
    """
    if field_type == "number":
        try:
            cleaned = cell.text.replace(",", "").replace("%", "").strip()
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except (ValueError, AttributeError):
            pass
    return cell.text


def _build_table_rows(
    rows: List[List[TableCell]],
    columns: List[TableColumn],
) -> List[Dict[str, Any]]:
    """Build Feishu Table row data.

    Args:
        rows: Parsed table cell data.
        columns: Column definitions (used for type conversion).

    Returns:
        List of Feishu row dicts.

    Feishu row format:
        {"col_0": "Alice", "col_1": 95}
    """
    feishu_rows: List[Dict[str, Any]] = []
    for row in rows:
        feishu_row: Dict[str, Any] = {}
        for idx, cell in enumerate(row):
            if idx >= len(columns):
                # Cells beyond the defined columns have no matching column
                # spec; drop them so the card stays valid for Feishu.
                break
            col = columns[idx]
            feishu_row[f"col_{idx}"] = _convert_cell_value(cell, col.field_type)
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
    tables: Optional[List[ParsedTable]] = None,
) -> Optional[Dict[str, Any]]:
    """Build a Feishu card that handles mixed content (text + tables).

    If the content contains tables, they are rendered as Table components.
    Non-table text is rendered as markdown elements.

    Args:
        markdown: Full markdown content that may include tables.
        title: Optional card header title.
        template: Card header color template.
        tables: Pre-parsed tables (from table_parser.parse_table). Pass this
                when the caller already parsed the content to avoid re-parsing.

    Returns:
        Complete Feishu card JSON dict, or None if no tables found
        (in which case use build_content_card or send as post message).
    """
    if tables is None:
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

    # Walk blank-line-split sections, mirroring parse_table's pre-split.
    # Without the split, _TABLE_BLOCK_RE would merge tables separated only
    # by a blank line into a single match, misaligning them with the
    # parsed tables and silently dropping tables from the card.
    table_idx = 0
    for section in _BLANK_LINE_RE.split(markdown):
        if not section.strip():
            continue

        last_end = 0
        for match in _TABLE_BLOCK_RE.finditer(section):
            # Text before this table
            before = section[last_end:match.start()].strip()
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

        # Remaining text after the last table in this section
        remaining = section[last_end:].strip()
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
