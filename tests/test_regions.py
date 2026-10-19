"""Offline checks for the simplified Turon regional flow."""
import os
import unittest
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, patch

for key in ('TELEGRAM_BOT_TOKEN', 'DRIVER_GROUP_1', 'DRIVER_GROUP_2', 'BRAND_GROUP'):
    os.environ.setdefault(key, '123:test' if key == 'TELEGRAM_BOT_TOKEN' else '-1001')

from bot import regions
from bot.handlers import brand, driver, start, operator
from bot.main import build_application_conversation


def update():
    msg = N(reply_text=AsyncMock(), text='', contact=None)
    return N(message=msg, effective_message=msg, callback_query=None,
             effective_chat=N(type='private'),
             effective_user=N(id=123, full_name='Test Person', username='example'))


def context(region):
    return N(user_data={'region': region}, bot_data={}, bot=N(get_chat_member=AsyncMock()))


class TuronRegions(unittest.IsolatedAsyncioTestCase):
    async def test_menu_has_only_requested_sections(self):
        ctx = context('namangan')
        u = update()
        await start.show_menu(u, ctx)
        text = u.message.reply_text.await_args.args[0]
        self.assertIn('Haydovchi', text)
        self.assertNotIn('Spectre', text)
        keyboard = start.main_keyboard('namangan')
        self.assertEqual([button.text for row in keyboard.keyboard for button in row],
                         [start.MENU_DRIVER, start.MENU_BRAND, start.MENU_CONTACT,
                          start.MENU_REGION])
        self.assertNotIn('OFFICE', repr(keyboard))

    async def test_both_regions_start_forms_without_subscription(self):
        with patch.dict(os.environ, {'TASHKENT_DRIVER_GROUP_1': '-2001',
                                     'TASHKENT_BRAND_GROUP': '-2002'}):
            for region in ('tashkent', 'namangan'):
                with self.subTest(region=region):
                    c = context(region)
                    d = update()
                    self.assertEqual(await driver.start_driver(d, c), driver.NAME)
                    self.assertTrue(d.message.reply_text.await_count)
                    c.bot.get_chat_member.assert_not_awaited()
                    c = context(region)
                    b = update()
                    self.assertEqual(await brand.start_brand(b, c), brand.BRAND_WARN)
                    c.bot.get_chat_member.assert_not_awaited()

    async def test_contact_uses_only_region_specific_new_setting(self):
        with patch.dict(os.environ, {'TURON_CONTACT_NAMANGAN': '+998 90 000 00 00'}, clear=False):
            c = context('namangan')
            u = update()
            await start.show_contact(u, c)
            self.assertIn('+998 90 000 00 00', u.message.reply_text.await_args.args[0])
        c = context('tashkent')
        u = update()
        await start.show_contact(u, c)
        self.assertNotIn('+998 90 000 00 00', u.message.reply_text.await_args.args[0])

    def test_routes_and_three_operator_actions(self):
        with patch.dict(os.environ, {'TASHKENT_DRIVER_GROUP_1': '-2001',
                                     'TASHKENT_BRAND_GROUP': '-2002'}):
            self.assertEqual(regions.driver_groups('tashkent'), ['-2001'])
            self.assertEqual(regions.application_group('tashkent', 'brand'), '-2002')
            self.assertEqual(regions.application_group('namangan', 'brand'), os.environ['BRAND_GROUP'])
            self.assertEqual(regions.application_group('tashkent', 'spectre'), '')
        keyboard = operator.build_operator_keyboard(1)
        actions = {button.callback_data.split(':')[1] for row in keyboard.inline_keyboard
                   for button in row}
        self.assertEqual(actions, {'ready', 'comment', 'progress'})
        build_application_conversation()
