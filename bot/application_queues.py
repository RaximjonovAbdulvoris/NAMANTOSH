"""Regional queue transfers and explicit deletion confirmation."""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from bot.regions import queue_group

logger = logging.getLogger(__name__)
_IN_FLIGHT = set()


def confirmation_keyboard(applicant_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"op:delete_yes:{applicant_id}"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data=f"op:delete_cancel:{applicant_id}"),
    ]])


async def save(context):
    application = getattr(context, "application", None)
    if application is not None:
        await application.update_persistence()
        if application.persistence:
            await application.persistence.flush()


async def delete_messages(bot, chat_id, ids):
    left = []
    for mid in ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except BadRequest as error:
            if "message to delete not found" not in str(error).lower():
                left.append(mid)
        except Exception:
            left.append(mid)
    return left


def forget(context, record):
    for name in ("applications", "app_messages"):
        store = context.bot_data.get(name, {})
        for key, value in list(store.items()):
            if value is record or (isinstance(value, dict) and value.get("application_key") == record["application_key"]):
                store.pop(key, None)
    context.bot_data.get("progress_state", {}).pop(record["application_key"], None)
    for name in ("operator_message_links", "pending_comments", "pending_user_replies"):
        store = context.bot_data.get(name, {})
        for key, value in list(store.items()):
            if value == record["application_key"]:
                store.pop(key, None)


async def cleanup(context, record):
    pending = record["queue_cleanup"]
    pending["photo_msg_ids"] = await delete_messages(context.bot, pending["group_chat_id"], pending["photo_msg_ids"])
    if not pending["photo_msg_ids"]:
        left = await delete_messages(context.bot, pending["group_chat_id"], [pending["kb_msg_id"]])
        if not left:
            record.pop("queue_cleanup")
            if record.get("queue_stage") in ("deleted", "archive"):
                forget(context, record)
    await save(context)
    return "queue_cleanup" not in record


async def handle(context, query, key, record, action, operator_id, keyboard):
    """Return True when a queue action has been handled."""
    pending = record.get("queue_cleanup")
    if key in _IN_FLIGHT:
        await query.message.reply_text("⏳ Ariza ustida amal bajarilmoqda.")
        return True
    if not pending and action not in ("incomplete", "other", "delete", "delete_yes", "delete_cancel"):
        return False
    _IN_FLIGHT.add(key)
    try:
        if pending:
            if not await cleanup(context, record):
                await query.message.reply_text("⚠️ Ayrim eski xabarlar o'chmadi. Bot huquqlarini tekshirib, qayta bosing; ariza qayta ko'chirilmaydi.")
            return True
        stage = record.get("queue_stage", "main")
        applicant = record["applicant_id"]
        progress = context.bot_data.get("progress_state", {}).get(key, False)
        if action in ("delete", "delete_yes", "delete_cancel"):
            if stage not in ("incomplete", "other"):
                await query.message.reply_text("O'chirish faqat Chala rasm va Boshqa park guruhlarida ishlaydi.")
                return True
            if action == "delete":
                await query.edit_message_reply_markup(reply_markup=confirmation_keyboard(applicant))
                record["delete_confirmation"] = operator_id
                await save(context)
                await query.message.reply_text("Arizani barcha rasmlari bilan o'chirishni tasdiqlaysizmi?")
                return True
            if record.get("delete_confirmation") != operator_id:
                await query.message.reply_text("Tasdiqlashni o'chirishni boshlagan operator bajarishi kerak.")
                return True
            if action == "delete_cancel":
                await query.edit_message_reply_markup(reply_markup=keyboard(applicant, progress, stage))
                record.pop("delete_confirmation", None)
                await save(context)
                return True
            record["queue_stage"] = "deleted"
            record["queue_cleanup"] = {
                "group_chat_id": record["group_chat_id"],
                "photo_msg_ids": list(record["photo_msg_ids"]), "kb_msg_id": record["kb_msg_id"],
            }
            await save(context)
            if not await cleanup(context, record):
                await query.message.reply_text("⚠️ Ayrim xabarlar o'chmadi. Botning huquqlarini tekshirib, qayta bosing.")
            return True
        if stage != "main":
            await query.message.reply_text("Ariza allaqachon maxsus guruhga o'tkazilgan.")
            return True
        target = queue_group(record["region"], action)
        if not target or not str(target).lstrip("-").isdigit() or not str(target).startswith("-") or str(target) == str(record["group_chat_id"]):
            await query.message.reply_text("⚠️ Shu regionning manzil guruhi sozlanmagan yoki joriy guruh bilan bir xil. Ariza saqlandi.")
            return True
        rollback = record.get("queue_rollback")
        if rollback:
            rollback["ids"] = await delete_messages(context.bot, rollback["chat_id"], rollback["ids"])
            await save(context)
            if rollback["ids"]:
                await query.message.reply_text("⚠️ Oldingi qisman nusxalarni o'chirish uchun botga manzil guruhida huquq bering.")
                return True
            record.pop("queue_rollback")
        copied = []
        try:
            originals = sorted(record["photo_msg_ids"])
            albums = record.get("media_albums")
            if albums is not None:
                metadata_ids = [mid for album in albums for mid in album["source_message_ids"]]
                if sorted(metadata_ids) != originals:
                    raise ValueError("Album metadata does not match source photos")
            if not originals:
                raise ValueError("Application photos missing")
            messages = list(await context.bot.copy_messages(chat_id=target, from_chat_id=record["group_chat_id"], message_ids=originals))
            copied.extend(m.message_id for m in messages)
            if len(messages) != len(originals):
                raise ValueError("Incomplete photo copy")
            mapping = dict(zip(originals, copied))
            info = await context.bot.copy_message(chat_id=target, from_chat_id=record["group_chat_id"],
                message_id=record["kb_msg_id"], reply_markup=keyboard(applicant, False, action))
            copied.append(info.message_id)
        except Exception:
            logger.warning("Queue transfer failed; originals retained", exc_info=True)
            left = await delete_messages(context.bot, target, copied)
            if left:
                record["queue_rollback"] = {"chat_id": target, "ids": left}
            await save(context)
            await query.message.reply_text("⚠️ Ko'chirish to'liq bajarilmadi. Asl ariza o'chirilmadi; ID va bot huquqlarini tekshiring.")
            return True
        source = {"group_chat_id": record["group_chat_id"], "photo_msg_ids": list(originals), "kb_msg_id": record["kb_msg_id"]}
        # Preserve the stable key for pending comments while indexing the new control message.
        record.update(group_chat_id=int(target), photo_msg_ids=copied[:-1], kb_msg_id=info.message_id,
            queue_stage=action, queue_cleanup=source, archive_state={"photos": {}, "kb": False})
        record.pop("delete_confirmation", None)
        for album in record.get("media_albums", []):
            album["source_message_ids"] = [mapping[mid] for mid in album["source_message_ids"]]
        new_key = (int(target), info.message_id)
        context.bot_data.setdefault("applications", {})[new_key] = record
        context.bot_data.setdefault("app_messages", {})[new_key] = record
        context.bot_data.get("progress_state", {}).pop(key, None)
        await save(context)
        if not await cleanup(context, record):
            await query.message.reply_text("⚠️ Ariza ko'chdi, ammo eski xabarlar to'liq o'chmadi. Huquqlarni tekshirib, qayta bosing.")
        return True
    finally:
        _IN_FLIGHT.discard(key)
