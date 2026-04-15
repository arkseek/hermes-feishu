"""Unit tests for card_builder module."""

import json
import pytest

from hermes_feishu.card_builder import (
    build_content_card,
    build_mixed_card,
    build_table_card,
    card_to_json,
)
from hermes_feishu.table_parser import ParsedTable, TableColumn, TableCell


class TestBuildTableCard:
    def _make_table(self):
        return ParsedTable(
            headers=[
                TableColumn(name="Name", index=0, field_type="text"),
                TableColumn(name="Score", index=1, field_type="number"),
            ],
            rows=[
                [TableCell(text="Alice"), TableCell(text="95")],
                [TableCell(text="Bob"), TableCell(text="87.5")],
            ],
            raw_markdown="| Name | Score |\n| --- | --- |\n| Alice | 95 |\n| Bob | 87.5 |",
        )

    def test_basic_structure(self):
        table = self._make_table()
        card = build_table_card(table)
        assert card["config"]["wide_screen_mode"] is True
        assert card["header"]["title"]["content"] == "📊 数据表格"
        assert card["header"]["template"] == "blue"

    def test_table_element(self):
        table = self._make_table()
        card = build_table_card(table)
        elements = card["elements"]
        assert len(elements) == 1
        assert elements[0]["tag"] == "table"

    def test_columns(self):
        table = self._make_table()
        card = build_table_card(table)
        columns = card["elements"][0]["columns"]
        assert len(columns) == 2
        assert columns[0]["field_type"] == "text"
        assert columns[0]["name"] == "Name"
        assert columns[1]["field_type"] == "number"
        assert columns[1]["name"] == "Score"

    def test_rows(self):
        table = self._make_table()
        card = build_table_card(table)
        rows = card["elements"][0]["rows"]
        assert len(rows) == 2
        assert rows[0][0]["text"] == "Alice"
        assert rows[0][1]["text"] == "95"
        assert rows[0][1]["value"] == 95
        # 87.5 stays as float
        assert rows[1][1]["value"] == 87.5

    def test_custom_title(self):
        table = self._make_table()
        card = build_table_card(table, title="Custom Title")
        assert card["header"]["title"]["content"] == "Custom Title"

    def test_custom_template(self):
        table = self._make_table()
        card = build_table_card(table, template="green")
        assert card["header"]["template"] == "green"


class TestBuildContentCard:
    def test_basic_markdown(self):
        card = build_content_card("**Hello** World")
        assert len(card["elements"]) == 1
        assert card["elements"][0]["tag"] == "markdown"
        assert card["elements"][0]["content"] == "**Hello** World"

    def test_with_title(self):
        card = build_content_card("Content", title="Title")
        assert card["header"]["title"]["content"] == "Title"
        assert len(card["elements"]) == 1

    def test_without_title(self):
        card = build_content_card("Content")
        assert "header" not in card
        assert len(card["elements"]) == 1

    def test_wide_screen(self):
        card = build_content_card("Content")
        assert card["config"]["wide_screen_mode"] is True


class TestBuildMixedCard:
    def test_with_table_returns_card(self):
        md = "Intro text\n| A | B |\n| --- | --- |\n| 1 | 2 |\nOutro"
        card = build_mixed_card(md)
        assert card is not None
        # Should have 3 elements: markdown (intro) + table + markdown (outro)
        assert len(card["elements"]) == 3
        assert card["elements"][0]["tag"] == "markdown"
        assert card["elements"][1]["tag"] == "table"
        assert card["elements"][2]["tag"] == "markdown"

    def test_without_table_returns_none(self):
        md = "Just text here, no tables"
        card = build_mixed_card(md)
        assert card is None

    def test_with_title(self):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
        card = build_mixed_card(md, title="Report")
        assert card is not None
        assert card["header"]["title"]["content"] == "Report"

    def test_only_table(self):
        md = "| Name | Value |\n| --- | --- |\n| X | 100 |"
        card = build_mixed_card(md)
        assert card is not None
        assert len(card["elements"]) == 1
        assert card["elements"][0]["tag"] == "table"

    def test_text_between_tables(self):
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |\nMiddle text\n| X | Y |\n| --- | --- |\n| a | b |"
        card = build_mixed_card(md)
        assert card is not None
        # table + markdown + table
        assert len(card["elements"]) == 3
        assert card["elements"][0]["tag"] == "table"
        assert card["elements"][1]["tag"] == "markdown"
        assert "Middle" in card["elements"][1]["content"]
        assert card["elements"][2]["tag"] == "table"


class TestCardToJson:
    def test_serialization(self):
        card = build_content_card("Test")
        json_str = card_to_json(card)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["config"]["wide_screen_mode"] is True

    def test_cjk_support(self):
        card = build_content_card("你好世界", title="测试标题")
        json_str = card_to_json(card)
        assert "你好世界" in json_str
        assert "测试标题" in json_str
        # ensure_ascii=False means CJK characters are not escaped
        assert "\\u" not in json_str
