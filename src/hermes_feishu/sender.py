"""Feishu API sender for Hermes Feishu plugin.

Handles sending interactive card messages via the Feishu Open API
using the lark-oapi SDK.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _get_credentials() -> tuple[str, str]:
    """Get Feishu app credentials from environment variables.

    Returns:
        Tuple of (app_id, app_secret).

    Raises:
        ValueError: If credentials are not configured.
    """
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise ValueError(
            "Feishu credentials not configured. "
            "Set FEISHU_APP_ID and FEISHU_APP_SECRET environment variables."
        )
    return app_id, app_secret


def _has_credentials() -> bool:
    """Check if Feishu credentials are available."""
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    return bool(app_id and app_secret)


def _add_reaction_to_message(
    client: Any,
    message_id: str,
    reaction_type: str,
) -> bool:
    """Add a reaction emoji to a message.

    Args:
        client: lark-oapi client instance.
        message_id: Feishu message ID.
        reaction_type: Feishu emoji_type string. Common values:
            - "DONE" (✅) - 表示已完成
            - "OK" (👌) - 表示确认
            - "THUMBSUP" (👍) - 表示点赞
            - "APPLAUSE" (👏) - 表示鼓掌
            See: https://open.feishu.cn/document/server-docs/im-v1/message-reaction/emojis-introduce

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Use the reaction API
        # POST /im/v1/messages/:message_id/reactions
        from lark_oapi.api.im.v1 import (
            CreateMessageReactionRequest,
            CreateMessageReactionRequestBody,
        )

        request = CreateMessageReactionRequest.builder() \
            .message_id(message_id) \
            .request_body(
                CreateMessageReactionRequestBody.builder()
                .reaction_type({"emoji_type": reaction_type})  # Object with emoji_type field
                .build()
            ).build()

        response = client.im.v1.message_reaction.create(request)

        if response.success():
            logger.info(
                "hermes_feishu: Reaction '%s' added to message %s",
                reaction_type, message_id,
            )
            return True
        else:
            logger.warning(
                "hermes_feishu: Failed to add reaction: code=%s, msg=%s",
                response.code, response.msg,
            )
            return False

    except Exception as e:
        logger.warning("hermes_feishu: Failed to add reaction: %s", e)
        return False


def send_card(
    card: Dict[str, Any],
    chat_id: str,
    *,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    add_reaction: Optional[str] = None,
) -> str:
    """Send a Feishu interactive card message.

    Uses the lark-oapi SDK to send the card to the specified chat.

    Args:
        card: Feishu card JSON dict (from card_builder module).
        chat_id: Feishu chat/group ID to send to.
        app_id: Override app ID (defaults to env var).
        app_secret: Override app secret (defaults to env var).
        add_reaction: Feishu emoji_type to add as reaction after sending.
                     Default: "DONE" (✅, indicates completed).
                     Pass empty string "" to skip reaction.
                     See: https://open.feishu.cn/document/server-docs/im-v1/message-reaction/emojis-introduce

    Returns:
        JSON string with send result: {"success": bool, "message_id": str|None, "error": str|None}
    """
    # Default reaction: DONE (✅) to indicate task completed
    if add_reaction is None:
        add_reaction = "DONE"
    if app_id is None or app_secret is None:
        try:
            resolved_id, resolved_secret = _get_credentials()
            app_id = app_id or resolved_id
            app_secret = app_secret or resolved_secret
        except ValueError as e:
            return json.dumps({"success": False, "error": str(e)})

    try:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import (
            CreateMessageRequest,
            CreateMessageRequestBody,
        )

        # Build client
        client = (
            lark.Client.builder()
            .app_id(app_id)
            .app_secret(app_secret)
            .log_level(lark.LogLevel.WARNING)
            .build()
        )

        # Build request
        card_json = json.dumps(card, ensure_ascii=False)
        
        # Debug: log the card JSON
        logger.debug("hermes_feishu: Card JSON: %s", card_json)
        
        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
                .content(card_json)
                .build()
            ).build()

        # Send
        response = client.im.v1.message.create(request)

        if not response.success():
            error_msg = f"Feishu API error: code={response.code}, msg={response.msg}"
            if response.data:
                error_msg += f", data={response.data}"
            logger.warning("hermes_feishu: %s", error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg,
                "code": response.code,
            })

        message_id = None
        if response.data and hasattr(response.data, "message_id"):
            message_id = response.data.message_id

        logger.info(
            "hermes_feishu: Card sent to chat %s, message_id=%s",
            chat_id, message_id,
        )

        # Add reaction if specified
        if add_reaction and message_id:
            _add_reaction_to_message(client, message_id, add_reaction)

        return json.dumps({
            "success": True,
            "message_id": message_id,
        })

    except ImportError:
        return json.dumps({
            "success": False,
            "error": "lark-oapi package not installed. Run: pip install lark-oapi",
        })
    except Exception as e:
        logger.exception("hermes_feishu: Failed to send card")
        return json.dumps({
            "success": False,
            "error": f"Failed to send card: {e}",
        })
