"""Markdown table parser for Hermes Feishu plugin.

Parses Markdown table syntax into structured data suitable for building
Feishu card Table components.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


# Regex to detect a Markdown table block.
# Matches lines like: | header1 | header2 | followed by | --- | --- | and data rows.
# Note: This regex is used within blank-line-split sections to avoid merging
# separate tables. See parse_table() for the splitting logic.
_TABLE_BLOCK_RE = re.compile(
    r"((?:^\|[^\n]+\|\s*\n"
    r"^\|(\s*:?-+:?\s*\|)+\s*\n?"
    r"(?:^\|[^\n]+\|\s*\n?)*)+)",
    re.MULTILINE,
)

# Blank line separator for splitting independent table sections.
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")

# Match a single table row: | cell1 | cell2 |
_ROW_RE = re.compile(r"^\|(.+)\|$", re.MULTILINE)

# Match the separator row: | --- | :---: | ---: |
# Each cell must contain at least one dash (-) or colon (:)
_SEPARATOR_RE = re.compile(r"^\|(\s*:?-+:?\s*\|)+\s*$", re.MULTILINE)


@dataclass
class TableCell:
    """A single cell in a parsed table."""

    text: str
    raw: str = ""

    def __post_init__(self):
        if not self.raw:
            self.raw = self.text


@dataclass
class TableColumn:
    """A column definition for a parsed table."""

    name: str
    index: int
    field_type: str = "text"  # "text" | "number"
    width: Optional[int] = None


@dataclass
class ParsedTable:
    """Result of parsing a Markdown table block."""

    headers: List[TableColumn] = field(default_factory=list)
    rows: List[List[TableCell]] = field(default_factory=list)
    raw_markdown: str = ""


def _parse_row(line: str) -> List[str]:
    """Parse a single table row into cell strings."""
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return []
    # Remove leading and trailing pipe, split by pipe
    inner = line[1:-1]
    cells = [cell.strip() for cell in inner.split("|")]
    return cells


def _infer_column_type(values: List[str]) -> str:
    """Infer the column type from its values.

    Returns "number" if all non-empty values are numeric, otherwise "text".
    """
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "text"
    for v in non_empty:
        # Remove common formatting (%, commas, etc.) and try to convert
        cleaned = v.replace(",", "").replace("%", "").strip()
        try:
            float(cleaned)
        except ValueError:
            return "text"
    return "number"


def parse_table(markdown: str) -> List[ParsedTable]:
    """Parse all Markdown table blocks from the given text.

    Splits input by blank lines first to avoid merging separate tables,
    then applies the table regex within each section.

    Args:
        markdown: Text that may contain one or more Markdown tables.

    Returns:
        List of ParsedTable objects, one per table block found.
    """
    tables: List[ParsedTable] = []

    # Pre-split by blank lines so independent tables are parsed separately
    sections = _BLANK_LINE_RE.split(markdown)
    for section in sections:
        if not section.strip():
            continue
        for match in _TABLE_BLOCK_RE.finditer(section):
            block = match.group(1)
            lines = [l for l in block.split("\n") if l.strip()]

            if len(lines) < 2:
                continue  # Need at least header + separator

            # Parse header row (first line)
            header_cells = _parse_row(lines[0])
            if not header_cells:
                continue

            # Verify separator row (second line)
            if not _SEPARATOR_RE.match(lines[1].strip()):
                continue

            # Build column definitions
            columns: List[TableColumn] = []
            for idx, name in enumerate(header_cells):
                columns.append(TableColumn(name=name, index=idx))

            # Parse data rows (lines after separator)
            data_rows: List[List[TableCell]] = []
            all_column_values: dict[int, List[str]] = {col.index: [] for col in columns}

            for line in lines[2:]:
                if _SEPARATOR_RE.match(line.strip()):
                    continue
                cells = _parse_row(line)
                if not cells:
                    continue
                row_cells: List[TableCell] = []
                for idx, cell_text in enumerate(cells):
                    if idx < len(columns):
                        tc = TableCell(text=cell_text)
                        row_cells.append(tc)
                        all_column_values[idx].append(cell_text)
                    else:
                        # Extra columns beyond header: append as text
                        tc = TableCell(text=cell_text)
                        row_cells.append(tc)
                data_rows.append(row_cells)

            # Infer column types
            for col in columns:
                col.field_type = _infer_column_type(all_column_values.get(col.index, []))

            tables.append(ParsedTable(
                headers=columns,
                rows=data_rows,
                raw_markdown=block.strip(),
            ))

    return tables


def contains_table(markdown: str) -> bool:
    """Check if the text contains any Markdown table syntax.

    Args:
        markdown: Text to check.

    Returns:
        True if at least one table block is detected.
    """
    for section in _BLANK_LINE_RE.split(markdown):
        if _TABLE_BLOCK_RE.search(section):
            return True
    return False


def split_table_and_text(markdown: str) -> Tuple[List[str], List[str]]:
    """Split markdown into table blocks and non-table text segments.

    Splits by blank lines first, then within each section separates
    text from tables using regex match positions.

    Args:
        markdown: Text that may contain tables and other content.

    Returns:
        Tuple of (table_blocks, text_segments).
        table_blocks: Raw markdown strings of each table found.
        text_segments: Non-table text portions, in original order.
    """
    table_blocks: List[str] = []
    text_segments: List[str] = []

    sections = _BLANK_LINE_RE.split(markdown)
    for section in sections:
        if not section.strip():
            continue

        # Check if section contains a table
        match = _TABLE_BLOCK_RE.search(section)
        if not match:
            stripped = section.strip()
            if stripped:
                text_segments.append(stripped)
            continue

        # Extract text before the first table in this section
        before = section[:match.start()].strip()
        if before:
            text_segments.append(before)

        # Collect all tables in this section (may be merged by regex)
        for t in parse_table(section):
            table_blocks.append(t.raw_markdown)

        # Extract text after the last table in this section
        last_end = 0
        for m in _TABLE_BLOCK_RE.finditer(section):
            last_end = m.end()
        after = section[last_end:].strip()
        if after:
            text_segments.append(after)

    return table_blocks, text_segments
