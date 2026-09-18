"""Remove obsolete brand controls without archiving or deleting applications."""
import logging

logger = logging.getLogger(__name__)


async def remove_legacy_brand_keyboards(application) -> None:
    seen = set()
    for store_name in ("applications", "app_messages"):
        for record in list(application.bot_data.get(store_name, {}).values()):
            if not isinstance(record, dict) or record.get("kind") != "brand":
                continue
            if record.get("brand_buttons_removed"):
                continue
            chat_id, message_id = record.get("group_chat_id"), record.get("kb_msg_id")
            if not chat_id or not message_id or (chat_id, message_id) in seen:
                continue
            seen.add((chat_id, message_id))
            try:
                await application.bot.edit_message_reply_markup(
                    chat_id=chat_id, message_id=message_id, reply_markup=None,
                )
                record["brand_buttons_removed"] = True
            except Exception:
                # Keep the record for a future startup retry. Old callbacks are
                # independently blocked, so failure cannot enable archiving.
                logger.warning("Old brand keyboard could not be removed; will retry on restart.")