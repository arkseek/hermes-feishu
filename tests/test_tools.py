"""Unit tests for tools module."""

import json
import pytest

from hermes_feishu.schemas import SEND_FEISHU_CARD_SCHEMA, SEND_FEISHU_TABLE_SCHEMA


class TestSchemas:
    def test_card_schema_has_required_fields(self):
        props = SEND_FEISHU_CARD_SCHEMA["parameters"]["properties"]
        assert "content" in props
        assert "title" in props
        assert "chat_id" in props
        assert "template" in props

    def test_card_schema_content_required(self):
        required = SEND_FEISHU_CARD_SCHEMA["parameters"]["required"]
        assert "content" in required

    def test_card_schema_template_enum(self):
        template = SEND_FEISHU_CARD_SCHEMA["parameters"]["properties"]["template"]
        assert "enum" in template
        assert "blue" in template["enum"]
        assert "green" in template["enum"]
        assert "red" in template["enum"]

    def test_card_schema_description_mentions_table(self):
        desc = SEND_FEISHU_CARD_SCHEMA["description"].lower()
        assert "table" in desc
        assert "feishu" in desc

    def test_table_schema_has_required_fields(self):
        props = SEND_FEISHU_TABLE_SCHEMA["parameters"]["properties"]
        assert "headers" in props
        assert "rows" in props

    def test_table_schema_required(self):
        required = SEND_FEISHU_TABLE_SCHEMA["parameters"]["required"]
        assert "headers" in required
        assert "rows" in required

    def test_table_schema_headers_type(self):
        headers = SEND_FEISHU_TABLE_SCHEMA["parameters"]["properties"]["headers"]
        assert headers["type"] == "array"
        assert headers["items"]["type"] == "string"

    def test_table_schema_rows_type(self):
        rows = SEND_FEISHU_TABLE_SCHEMA["parameters"]["properties"]["rows"]
        assert rows["type"] == "array"
        assert rows["items"]["type"] == "array"


class TestToolHandlers:
    """Test tool handlers without actual Feishu API calls."""

    def test_card_no_content_returns_error(self):
        from hermes_feishu.tools import send_feishu_card
        result = json.loads(send_feishu_card({}))
        assert "error" in result

    def test_card_no_chat_id_returns_error(self):
        from hermes_feishu.tools import send_feishu_card
        result = json.loads(send_feishu_card({"content": "test"}))
        assert "error" in result

    def test_card_with_chat_id_attempts_send(self):
        from hermes_feishu.tools import send_feishu_card
        # With no credentials, should still get a result (error about credentials)
        result = json.loads(send_feishu_card(
            {"content": "| A | B |\n| --- | --- |\n| 1 | 2 |"},
            chat_id="test_chat",
        ))
        # Should get some result (success or error about credentials)
        assert "success" in result or "error" in result

    def test_table_no_headers_returns_error(self):
        from hermes_feishu.tools import send_feishu_table
        result = json.loads(send_feishu_table({}))
        assert "error" in result

    def test_table_no_rows_returns_error(self):
        from hermes_feishu.tools import send_feishu_table
        result = json.loads(send_feishu_table({"headers": ["A", "B"]}))
        assert "error" in result

    def test_table_no_chat_id_returns_error(self):
        from hermes_feishu.tools import send_feishu_table
        result = json.loads(send_feishu_table({
            "headers": ["A", "B"],
            "rows": [["1", "2"]],
        }))
        assert "error" in result

    def test_table_builds_valid_card_structure(self):
        """Verify the tool builds correct card structure without actually sending."""
        from hermes_feishu.tools import send_feishu_table
        from unittest.mock import patch

        mock_result = json.dumps({"success": True, "message_id": "om_xxx"})
        with patch("hermes_feishu.tools.send_card", return_value=mock_result):
            result = json.loads(send_feishu_table(
                {"headers": ["Name", "Score"], "rows": [["Alice", "95"]]},
                chat_id="test_chat",
            ))
        assert result["success"] is True

    def test_card_with_table_content(self):
        """Verify card tool handles table content correctly."""
        from hermes_feishu.tools import send_feishu_card
        from unittest.mock import patch
        import hermes_feishu.card_builder as cb

        # Verify build_mixed_card is called with table content
        content = "| Name | Value |\n| --- | --- |\n| Key | 100 |"
        card = cb.build_mixed_card(content)
        assert card is not None
        assert any(e["tag"] == "table" for e in card["elements"])

    def test_reaction_defaults_to_done(self):
        from hermes_feishu.tools import send_feishu_card
        from unittest.mock import patch

        captured = {}

        def fake_send(card, chat_id, add_reaction=None):
            captured["add_reaction"] = add_reaction
            return json.dumps({"success": True})

        with patch("hermes_feishu.tools.send_card", side_effect=fake_send):
            send_feishu_card({"content": "hi"}, chat_id="x")
        assert captured["add_reaction"] == "DONE"

    def test_reaction_empty_string_skips_reaction(self):
        """An explicit empty reaction must reach send_card as '' (skip),
        not be swallowed by a truthiness fallback to 'DONE'."""
        from hermes_feishu.tools import send_feishu_card, send_feishu_table
        from unittest.mock import patch

        captured = []

        def fake_send(card, chat_id, add_reaction=None):
            captured.append(add_reaction)
            return json.dumps({"success": True})

        with patch("hermes_feishu.tools.send_card", side_effect=fake_send):
            send_feishu_card({"content": "hi", "reaction": ""}, chat_id="x")
            send_feishu_table(
                {"headers": ["A"], "rows": [["1"]], "reaction": ""}, chat_id="x"
            )
        assert captured == ["", ""]

    def test_table_ragged_rows_normalized(self):
        """Rows with more/fewer cells than headers are truncated/padded so
        row keys always align with the column specs."""
        from hermes_feishu.tools import send_feishu_table
        from unittest.mock import patch

        captured = {}

        def fake_send(card, chat_id, add_reaction=None):
            captured["card"] = card
            return json.dumps({"success": True})

        with patch("hermes_feishu.tools.send_card", side_effect=fake_send):
            send_feishu_table(
                {"headers": ["A", "B"], "rows": [["x", "y", "z"], ["w"]]},
                chat_id="x",
            )
        table = captured["card"]["elements"][0]
        assert [c["name"] for c in table["columns"]] == ["col_0", "col_1"]
        assert table["rows"][0] == {"col_0": "x", "col_1": "y"}  # extra dropped
        assert table["rows"][1] == {"col_0": "w", "col_1": ""}   # missing padded


class TestPreLlmCallHook:
    def test_feishu_platform_returns_context(self):
        from hermes_feishu import _on_pre_llm_call
        result = _on_pre_llm_call(platform="feishu", is_first_turn=True)
        assert result is not None
        assert "context" in result
        assert "table" in result["context"].lower()

    def test_lark_platform_returns_context(self):
        from hermes_feishu import _on_pre_llm_call
        result = _on_pre_llm_call(platform="lark", is_first_turn=True)
        assert result is not None

    def test_non_feishu_platform_returns_none(self):
        from hermes_feishu import _on_pre_llm_call
        result = _on_pre_llm_call(platform="telegram", is_first_turn=True)
        assert result is None

    def test_non_first_turn_still_injects_context(self):
        """Context is injected on every turn, not just the first.

        The implementation intentionally re-injects on every turn to
        ensure the LLM remembers the formatting instructions throughout
        a multi-turn conversation.
        """
        from hermes_feishu import _on_pre_llm_call
        result = _on_pre_llm_call(platform="feishu", is_first_turn=False)
        assert result is not None
        assert "context" in result

    def test_no_platform_returns_none(self):
        from hermes_feishu import _on_pre_llm_call
        result = _on_pre_llm_call(platform="", is_first_turn=True)
        assert result is None
