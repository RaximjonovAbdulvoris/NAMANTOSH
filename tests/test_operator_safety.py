import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

for _key, _value in {
    "TELEGRAM_BOT_TOKEN": "test-token",
    "DRIVER_GROUP_1": "11",
    "DRIVER_GROUP_2": "12",
    "DRIVER_GROUP_3": "13",
    "DRIVER_GROUP_4": "14",
    "BRAND_GROUP": "21",
}.items():
    os.environ.setdefault(_key, _value)

from bot.handlers import operator


class FakeMessage:
    def __init__(self, message_id, chat_id):
        self.message_id = message_id
        self.chat_id = chat_id
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        return FakeMessage(self.message_id + 1000, self.chat_id)


class FakeQuery:
    def __init__(self, data, message):
        self.data = data
        self.message = message
        self.deleted = False

    async def answer(self, *args, **kwargs):
        return None

    async def delete_message(self):
        self.deleted = True

    async def edit_message_reply_markup(self, **kwargs):
        return None


class FakeBot:
    def __init__(self, fail_ids=()):
        self.copies = []
        self.deletes = []
        self.sent = []
        self.sent_objects = []
        self.fail_ids = set(fail_ids)
        self.next_id = 500

    async def copy_message(self, **kwargs):
        if kwargs["message_id"] in self.fail_ids:
            raise RuntimeError("copy failed")
        self.copies.append(kwargs)
        return object()

    async def delete_message(self, **kwargs):
        self.deletes.append(kwargs)

    async def send_message(self, **kwargs):
        self.next_id += 1
        self.sent.append(kwargs)
        message = FakeMessage(self.next_id, kwargs["chat_id"])
        self.sent_objects.append(message)
        return message


def _update(data, message, user_id=9, chat_id=None):
    query = FakeQuery(data, message)
    return SimpleNamespace(
        callback_query=query,
        effective_chat=SimpleNamespace(id=chat_id or message.chat_id),
        effective_user=SimpleNamespace(id=user_id, full_name="Operator", username="op"),
    )


class OperatorSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_archive_retry_does_not_duplicate_successful_copies(self):
        context = self._context(FakeBot(fail_ids=[20]))
        key = self._register(context, 9, "tashkent", 100, 20)
        record = context.bot_data["applications"][key]
        self.assertFalse(await operator._archive_application(context.bot, record, "-300"))
        context.bot.fail_ids.clear()
        self.assertTrue(await operator._archive_application(context.bot, record, "-300"))
        self.assertEqual(len(context.bot.copies), 2)
        # A changed archive destination must receive all messages, not just
        # the remaining messages from a previous destination.
        self.assertTrue(await operator._archive_application(context.bot, record, "-301"))
        self.assertEqual(len(context.bot.copies), 4)

    def _context(self, bot=None):
        return SimpleNamespace(bot_data={}, bot=bot or FakeBot())

    def _register(self, context, applicant, region, group, kb, kind="driver"):
        return operator.register_application(
            context,
            applicant_id=applicant,
            region=region,
            kind=kind,
            group_chat_id=group,
            photo_msg_ids=[kb + 1],
            kb_msg_id=kb,
            applicant_name=f"Applicant {applicant}",
        )

    async def test_same_user_records_resolve_by_chat_and_keyboard(self):
        context = self._context()
        first = self._register(context, 9, "namangan", 101, 201)
        second = self._register(context, 9, "tashkent", 102, 202)
        self.assertEqual(
            operator._find_application(context, 9, 101, 201)[0], first
        )
        self.assertEqual(
            operator._find_application(context, 9, 102, 202)[0], second
        )

    async def test_ready_uses_stored_region_destination(self):
        bot = FakeBot()
        context = self._context(bot)
        self._register(context, 9, "tashkent", 102, 202)
        message = FakeMessage(202, 102)
        update = _update("op:ready:9", message, chat_id=102)
        with patch.object(operator, "archive_group", side_effect=lambda region: {
            "tashkent": "tashkent-archive",
        }.get(region, "")) as destination:
            await operator.on_operator_button(update, context)
        destination.assert_called_once_with("tashkent")
        self.assertTrue(bot.copies)
        self.assertTrue(all(item["chat_id"] == "tashkent-archive" for item in bot.copies))

    async def test_archive_failure_never_deletes_originals(self):
        bot = FakeBot(fail_ids={203})
        context = self._context(bot)
        self._register(context, 9, "namangan", 103, 203)
        message = FakeMessage(203, 103)
        update = _update("op:ready:9", message, chat_id=103)
        with patch.object(operator, "archive_group", return_value="archive"):
            await operator.on_operator_button(update, context)
        self.assertEqual(bot.deletes, [])
        self.assertTrue(any("o‘chirilmadi" in text for text in message.replies))

    async def test_comment_reply_keeps_original_branch(self):
        bot = FakeBot()
        context = self._context(bot)
        key = self._register(context, 9, "tashkent", 104, 204)
        message = FakeMessage(204, 104)
        update = _update("op:comment:9", message, user_id=77, chat_id=104)
        await operator.on_operator_button(update, context)
        operator_update = SimpleNamespace(
            message=SimpleNamespace(text="Toshkent savoli", reply_text=FakeMessage(1, 104).reply_text),
            effective_chat=SimpleNamespace(id=104),
            effective_user=SimpleNamespace(id=77, full_name="Operator", username="op"),
        )
        await operator.on_operator_text_in_group(operator_update, context)
        user_messages = [item for item in bot.sent if item["chat_id"] == 9]
        self.assertEqual(len(user_messages), 1)
        self.assertIn("WB HUMO Toshkent", user_messages[0]["text"])
        self.assertEqual(
            context.bot_data["operator_message_links"][
                (104, bot.sent_objects[-1].message_id)
            ],
            key,
        )