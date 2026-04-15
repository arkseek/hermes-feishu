"""Tool schemas for Hermes Feishu plugin.

Defines the JSON schemas that the LLM uses to decide when and how
to invoke the feishu card/table tools.
"""

SEND_FEISHU_CARD_SCHEMA = {
    "name": "send_feishu_card",
    "description": (
        "Send a rich card message to the current Feishu chat. "
        "Use this when you need to display tabular data, structured content, "
        "or formatted information that requires rich rendering. "
        "The card supports Markdown text, tables (parsed from Markdown table syntax), "
        "and interactive elements. "
        "IMPORTANT: Feishu post messages do NOT support Markdown tables. "
        "If your response contains a table (| col | col | format), "
        "you MUST use this tool to render it properly."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "Markdown content for the card. If it contains Markdown table "
                    "syntax (| col1 | col2 |\\n| --- | --- |\\n| data | data |), "
                    "the table will be automatically rendered using Feishu's Table "
                    "component. Non-table content is rendered as Markdown text."
                ),
            },
            "title": {
                "type": "string",
                "description": (
                    "Card header title. If not provided, defaults to '📊 数据表格' "
                    "when content contains tables, or no title for text-only cards."
                ),
                "default": "",
            },
            "chat_id": {
                "type": "string",
                "description": (
                    "Feishu chat ID to send to. Usually provided automatically "
                    "via context. Only specify if you need to send to a different chat."
                ),
                "default": "",
            },
            "template": {
                "type": "string",
                "description": (
                    "Card header color template. Options: blue, wathet, turquoise, "
                    "green, yellow, orange, red, carmine, violet, purple, indigo, grey."
                ),
                "default": "blue",
                "enum": [
                    "blue", "wathet", "turquoise", "green", "yellow",
                    "orange", "red", "carmine", "violet", "purple",
                    "indigo", "grey",
                ],
            },
        },
        "required": ["content"],
    },
}

SEND_FEISHU_TABLE_SCHEMA = {
    "name": "send_feishu_table",
    "description": (
        "Send a structured table as a Feishu card message. "
        "Use this when you have tabular data in a structured format. "
        "The table will be rendered using Feishu's Table component with proper "
        "column types (text/number auto-detected). "
        "Prefer this tool over send_feishu_card when you have structured data "
        "rather than Markdown text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "headers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Column header names.",
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "description": "Table data rows. Each row is an array of cell values (strings).",
            },
            "title": {
                "type": "string",
                "description": "Card header title. Defaults to '📊 数据表格'.",
                "default": "",
            },
            "chat_id": {
                "type": "string",
                "description": (
                    "Feishu chat ID. Usually auto-detected from context."
                ),
                "default": "",
            },
            "template": {
                "type": "string",
                "description": "Card header color. Default: blue.",
                "default": "blue",
                "enum": [
                    "blue", "wathet", "turquoise", "green", "yellow",
                    "orange", "red", "carmine", "violet", "purple",
                    "indigo", "grey",
                ],
            },
        },
        "required": ["headers", "rows"],
    },
}
