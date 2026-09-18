"""Offline coverage: no Telegram requests and no real application data."""
import os
import unittest
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, patch

for key in ("TELEGRAM_BOT_TOKEN", "DRIVER_GROUP_1", "DRIVER_GROUP_2",
            "DRIVER_GROUP_3", "DRIVER_GROUP_4", "BRAND_GROUP"):
    os.environ.setdefault(key, "123:test" if key == "TELEGRAM_BOT_TOKEN" else "-1001")

from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop, ConversationHandler

from bot import regions, subscription
from bot.handlers import brand, driver, start
from bot.main import build_application_conversation, intercept_pending_reply


def context(region=None):
    return N(
        user_data={"region": region} if region else {},
        bot_data={},
        bot=N(
            get_chat_member=AsyncMock(return_value=N(status="member")),
            send_message=AsyncMock(return_value=N(message_id=90)),
            send_media_group=AsyncMock(return_value=[N(message_id=80), N(message_id=81)]),
        ),
    )


def update(text=""):
    message = N(
        text=text, message_id=1, reply_text=AsyncMock(), reply_photo=AsyncMock(),
        contact=None,
    )
    return N(
        message=message, effective_message=message, callback_query=None,
        effective_chat=N(id=123, type="private"),
        effective_user=N(id=123, full_name="Test Applicant", username="test_applicant"),
    )


def callback(data):
    result = update()
    result.callback_query = N(
        data=data, message=result.message, answer=AsyncMock(),
        edit_message_text=AsyncMock(), edit_message_reply_markup=AsyncMock(),
    )
    return result


class RegionalTests(unittest.IsolatedAsyncioTestCase):
    async def test_region_must_be_confirmed_and_old_buttons_cannot_change_it(self):
        ctx = context()
        await start.start(update(), ctx)
        nonce = ctx.user_data["region_choice_nonce"]
        await start.on_region_choice(callback(f"region:pick:tashkent:{nonce}"), ctx)
        self.assertIsNone(regions.get_region(ctx))
        await start.on_region_choice(callback(f"region:confirm:tashkent:{nonce}"), ctx)
        self.assertEqual(regions.get_region(ctx), "tashkent")
        await start.on_region_choice(callback(f"region:confirm:namangan:{nonce}"), ctx)
        self.assertEqual(regions.get_region(ctx), "tashkent")

    async def test_back_and_switch_discard_unconfirmed_or_partial_form(self):
        ctx = context("namangan")
        ctx.user_data["name"] = "Old form"
        await start.start(update(), ctx)
        self.assertNotIn("name", ctx.user_data)
        self.assertIsNone(regions.get_region(ctx))
        nonce = ctx.user_data["region_choice_nonce"]
        await start.on_region_choice(callback(f"region:pick:tashkent:{nonce}"), ctx)
        await start.on_region_choice(callback(f"region:back:tashkent:{nonce}"), ctx)
        await start.on_region_choice(callback(f"region:confirm:tashkent:{nonce}"), ctx)
        self.assertIsNone(regions.get_region(ctx))

    async def test_menus_and_namangan_only_handlers(self):
        def buttons(region):
            return [button.text for row in start.main_keyboard(region).keyboard for button in row]
        self.assertIn(start.MENU_CONTACT, buttons("namangan"))
        self.assertNotIn(start.MENU_SPECTRE, buttons("namangan"))
        self.assertIn(start.MENU_SPECTRE, buttons("tashkent"))
        self.assertNotIn(start.MENU_CONTACT, buttons("tashkent"))
        self.assertNotIn(start.MENU_OFFICE, buttons("tashkent"))
        msg = update()
        await start.show_office(msg, context("tashkent"))
        msg.message.reply_photo.assert_not_awaited()
        await start.show_contact(msg, context("tashkent"))
        self.assertNotIn(start.CONTACT_TEXT, msg.message.reply_text.call_args.args[0])

    async def test_all_forms_need_confirmed_region(self):
        for handler in (driver.start_driver, brand.start_brand, brand.start_spectre):
            ctx = context()
            result = await handler(update(), ctx)
            self.assertEqual(result, ConversationHandler.END)
            ctx.bot.get_chat_member.assert_not_awaited()
            ctx.bot.send_message.assert_not_awaited()

    async def test_missing_tashkent_routes_do_not_collect_or_send(self):
        with patch.dict(os.environ, {
            "TASHKENT_DRIVER_GROUP_1": "", "TASHKENT_DRIVER_GROUP_2": "",
            "TASHKENT_BRAND_GROUP": "", "TASHKENT_SPECTRE_GROUP": "",
        }):
            for handler in (driver.start_driver, brand.start_brand, brand.start_spectre):
                ctx = context("tashkent")
                self.assertEqual(await handler(update(), ctx), ConversationHandler.END)
                ctx.bot.send_message.assert_not_awaited()
                ctx.bot.get_chat_member.assert_not_awaited()
                self.assertEqual(regions.get_region(ctx), "tashkent")

    async def test_namangan_cannot_enter_spectre(self):
        ctx = context("namangan")
        self.assertEqual(await brand.start_spectre(update(), ctx), ConversationHandler.END)
        ctx.bot.get_chat_member.assert_not_awaited()

    async def test_shared_membership_gate_fails_closed(self):
        ctx = context("tashkent")
        ctx.bot.get_chat_member.return_value = N(status="left")
        self.assertFalse(await subscription.require_subscription(update(), ctx, callback_data="test"))
        ctx.bot.get_chat_member.side_effect = TelegramError("unavailable")
        self.assertFalse(await subscription.require_subscription(update(), ctx, callback_data="test"))
        self.assertEqual(ctx.bot.get_chat_member.call_args.kwargs["chat_id"], "@WB_HUMO_TAXI")

    async def test_brand_and_spectre_full_question_flow_routes_by_region_and_kind(self):
        destinations = {("namangan", "brand"): "-201", ("tashkent", "brand"): "-202",
                        ("tashkent", "spectre"): "-203"}
        with patch("bot.regions.BRAND_GROUP", "-201"), patch.dict(os.environ, {
            "TASHKENT_BRAND_GROUP": "-202", "TASHKENT_SPECTRE_GROUP": "-203",
        }):
            for (region, kind), destination in destinations.items():
                ctx = context(region)
                result = await (brand.start_spectre if kind == "spectre" else brand.start_brand)(update(), ctx)
                if kind == "brand":
                    self.assertEqual(result, brand.BRAND_WARN)
                    await brand.brand_warn(update(), ctx)
                else:
                    self.assertEqual(result, brand.BRAND_NAME)
                for handler, answer in (
                    (brand.brand_get_name, "Test Applicant"),
                    (brand.brand_get_phone, "+998901234567"),
                    (brand.brand_get_model, "Cobalt"),
                    (brand.brand_get_year, "2020"),
                    (brand.brand_get_color, "Oq"),
                    (brand.brand_get_plate, "01A123BC"),
                ):
                    await handler(update(answer), ctx)
                self.assertEqual(str(ctx.bot.send_message.call_args.kwargs["chat_id"]), destination)
                self.assertIsNone(ctx.bot.send_message.call_args.kwargs["reply_markup"])
                self.assertFalse(ctx.bot_data.get("applications"))
                self.assertFalse(ctx.bot_data.get("app_messages"))
                self.assertEqual(ctx.user_data, {"region": region})

    async def test_driver_routes_and_registers_separate_branch(self):
        with patch("bot.regions.DRIVER_GROUPS", ["-301"]), patch.dict(os.environ, {
            "TASHKENT_DRIVER_GROUP_1": "-302", "TASHKENT_DRIVER_GROUP_2": "",
        }), patch("bot.handlers.driver.next_index", return_value=0):
            for region, destination in (("namangan", "-301"), ("tashkent", "-302")):
                ctx = context(region)
                self.assertEqual(await driver.start_driver(update(), ctx), driver.NAME)
                ctx.user_data.update({
                    "name": "Test", "phone": "+998901234567", "car_plate": "01A123BC",
                    "user_id": 123, "passport_front": "photo1", "passport_back": "photo2",
                    "selfie": "photo3", "litsenziya": "photo4",
                })
                await driver._send_to_driver_group(ctx)
                self.assertEqual(str(ctx.bot.send_message.call_args.kwargs["chat_id"]), destination)
                self.assertTrue(all(str(call.kwargs["chat_id"]) == destination
                                    for call in ctx.bot.send_media_group.call_args_list))
                record = next(iter(ctx.bot_data["applications"].values()))
                self.assertEqual(record["region"], region)

    async def test_cancel_keeps_region_but_clears_form(self):
        ctx = context("tashkent")
        ctx.user_data["b_name"] = "partial"
        await start.cancel(update(), ctx)
        self.assertEqual(ctx.user_data, {"region": "tashkent"})

    async def test_pending_reply_does_not_also_become_form_answer(self):
        ctx = context("tashkent")
        ctx.bot_data["pending_user_replies"] = {123: "test"}
        with patch("bot.main.on_user_reply_message", new_callable=AsyncMock) as reply:
            with self.assertRaises(ApplicationHandlerStop):
                await intercept_pending_reply(update("My reply"), ctx)
            reply.assert_awaited_once()
        await intercept_pending_reply(update(start.MENU_REGION), ctx)
        self.assertNotIn(123, ctx.bot_data["pending_user_replies"])

    def test_single_conversation_has_both_nonoverlapping_state_sets(self):
        conversation = build_application_conversation()
        self.assertIn(driver.NAME, conversation.states)
        self.assertIn(brand.BRAND_NAME, conversation.states)
        self.assertTrue(conversation.allow_reentry)


if __name__ == "__main__":
    unittest.main()