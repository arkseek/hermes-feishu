"""Unit tests for table_parser module."""

import pytest

from hermes_feishu.table_parser import (
    ParsedTable,
    TableColumn,
    TableCell,
    contains_table,
    parse_table,
    split_table_and_text,
    _infer_column_type,
    _parse_row,
)


class TestParseRow:
    def test_basic_row(self):
        result = _parse_row("| Name | Age |")
        assert result == ["Name", "Age"]

    def test_row_with_spaces(self):
        result = _parse_row("|  Hello World  |  Test  |")
        assert result == ["Hello World", "Test"]

    def test_single_column(self):
        result = _parse_row("| Only |")
        assert result == ["Only"]

    def test_empty_cells(self):
        result = _parse_row("| A | | C |")
        assert result == ["A", "", "C"]

    def test_not_a_row(self):
        result = _parse_row("This is not a table row")
        assert result == []

    def test_cell_with_pipe_in_content(self):
        result = _parse_row("| a | b | c | d |")
        assert len(result) == 4

    def test_cell_with_special_chars(self):
        result = _parse_row("| $100 | 50% | 1,000 |")
        assert result == ["$100", "50%", "1,000"]


class TestInferColumnType:
    def test_all_numbers(self):
        values = ["1", "2", "3", "10.5"]
        assert _infer_column_type(values) == "number"

    def test_mixed(self):
        values = ["1", "hello", "3"]
        assert _infer_column_type(values) == "text"

    def test_all_text(self):
        values = ["apple", "banana", "cherry"]
        assert _infer_column_type(values) == "text"

    def test_empty(self):
        assert _infer_column_type([]) == "text"

    def test_numbers_with_commas(self):
        values = ["1,000", "2,500", "10,000"]
        assert _infer_column_type(values) == "number"

    def test_numbers_with_percent(self):
        values = ["50%", "75%", "100%"]
        assert _infer_column_type(values) == "number"

    def test_all_empty_strings(self):
        assert _infer_column_type(["", "", ""]) == "text"


class TestContainsTable:
    def test_has_table(self):
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        assert contains_table(md) is True

    def test_no_table(self):
        md = "Just some text without a table."
        assert contains_table(md) is False

    def test_table_in_text(self):
        md = "Here is some data:\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\nDone."
        assert contains_table(md) is True

    def test_pipe_in_code_block(self):
        md = "```\n| this | is | code |\n```\n| real | table |\n| --- | --- |"
        # The code block pipes don't form a valid table (no separator row),
        # but the real table after the code block should be detected.
        assert contains_table(md) is True


class TestParseTable:
    def test_basic_table(self):
        md = "| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |"
        tables = parse_table(md)
        assert len(tables) == 1

        table = tables[0]
        assert len(table.headers) == 2
        assert table.headers[0].name == "Name"
        assert table.headers[1].name == "Age"
        assert len(table.rows) == 2
        assert table.rows[0][0].text == "Alice"
        assert table.rows[0][1].text == "30"

    def test_table_with_alignments(self):
        md = "| Left | Center | Right |\n| :--- | :---: | ---: |\n| A | B | C |"
        tables = parse_table(md)
        assert len(tables) == 1
        assert len(tables[0].headers) == 3
        assert len(tables[0].rows) == 1

    def test_single_row_table(self):
        md = "| H1 | H2 |\n| --- | --- |"
        tables = parse_table(md)
        assert len(tables) == 1
        assert len(tables[0].headers) == 2
        assert len(tables[0].rows) == 0

    def test_multiple_tables(self):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n| X | Y |\n| --- | --- |\n| a | b |"
        tables = parse_table(md)
        assert len(tables) == 2

    def test_column_type_inference(self):
        md = "| Name | Score | Count |\n| --- | --- | --- |\n| Alice | 95.5 | 100 |\n| Bob | 87 | 200 |"
        tables = parse_table(md)
        table = tables[0]
        assert table.headers[0].field_type == "text"
        assert table.headers[1].field_type == "number"
        assert table.headers[2].field_type == "number"

    def test_table_with_empty_cells(self):
        md = "| A | B |\n| --- | --- |\n| hello | |\n|  | world |"
        tables = parse_table(md)
        table = tables[0]
        assert table.rows[0][1].text == ""
        assert table.rows[1][0].text == ""

    def test_table_with_markdown_in_cells(self):
        md = "| Feature | Status |\n| --- | --- |\n| **Bold** | `code` |\n| *Italic* | [link](url) |"
        tables = parse_table(md)
        table = tables[0]
        assert table.rows[0][0].text == "**Bold**"
        assert table.rows[1][0].text == "*Italic*"

    def test_no_table_returns_empty(self):
        tables = parse_table("No tables here")
        assert tables == []

    def test_preserves_raw_markdown(self):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        tables = parse_table(md)
        assert tables[0].raw_markdown == md


class TestSplitTableAndText:
    def test_text_before_table(self):
        md = "Here is the data:\n| A | B |\n| --- | --- |\n| 1 | 2 |"
        table_blocks, text_segments = split_table_and_text(md)
        assert len(table_blocks) == 1
        assert len(text_segments) == 1
        assert "Here is the data" in text_segments[0]

    def test_table_surrounded_by_text(self):
        md = "Intro\n| A | B |\n| --- | --- |\n| 1 | 2 |\nOutro"
        table_blocks, text_segments = split_table_and_text(md)
        assert len(table_blocks) == 1
        assert len(text_segments) == 2
        assert "Intro" in text_segments[0]
        assert "Outro" in text_segments[1]

    def test_no_table(self):
        md = "Just text here"
        table_blocks, text_segments = split_table_and_text(md)
        assert len(table_blocks) == 0
        assert len(text_segments) == 1

    def test_multiple_tables_with_text(self):
        md = "First:\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\nSecond:\n| X | Y |\n| --- | --- |\n| a | b |\nEnd"
        table_blocks, text_segments = split_table_and_text(md)
        assert len(table_blocks) == 2
        assert len(text_segments) == 3
