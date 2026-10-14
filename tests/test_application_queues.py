import os
import tempfile
import unittest
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, patch

for name in ('TELEGRAM_BOT_TOKEN', 'DRIVER_GROUP_1', 'DRIVER_GROUP_2', 'BRAND_GROUP'):
    os.environ.setdefault(name, 'test-token')
from bot.handlers import operator as op
from bot import regions
from bot.route_settings import save_settings


class QueueTests(unittest.IsolatedAsyncioTestCase):
    def setup_case(self, region='namangan', stage='main'):
        bot = N(copy_messages=AsyncMock(return_value=[N(message_id=100), N(message_id=101)]),
                copy_message=AsyncMock(return_value=N(message_id=102)),
                delete_message=AsyncMock(), send_message=AsyncMock(), id=555)
        ctx = N(bot=bot, bot_data={}, application=N(update_persistence=AsyncMock(), persistence=N(flush=AsyncMock())))
        key = op.register_application(ctx, applicant_id=9, region=region, kind='driver',
                                     group_chat_id=-10, photo_msg_ids=[11, 12], kb_msg_id=13,
                                     media_albums=[{'source_message_ids': [11, 12], 'photos': [{'file_id': 'a'}, {'file_id': 'b'}]}])
        record = ctx.bot_data['applications'][key]
        record['queue_stage'] = stage
        return ctx, record, key

    def update(self, record, action, user=77):
        message = N(message_id=record['kb_msg_id'], chat_id=record['group_chat_id'], text='', caption='', reply_text=AsyncMock(), from_user=N(id=555))
        query = N(data=f'op:{action}:9', message=message, answer=AsyncMock(), edit_message_reply_markup=AsyncMock())
        return N(callback_query=query, effective_chat=N(id=message.chat_id), effective_user=N(id=user, full_name='Operator'))

    async def test_both_regions_both_queues_reset_and_archive_metadata(self):
        for region in ('namangan', 'tashkent'):
            for action in ('incomplete', 'other'):
                ctx, record, key = self.setup_case(region)
                ctx.bot_data['progress_state'] = {key: True}
                with patch('bot.application_queues.queue_group', return_value='-20') as route:
                    await op.on_operator_button(self.update(record, action), ctx)
                route.assert_called_once_with(region, action)
                self.assertEqual(record['group_chat_id'], -20)
                self.assertEqual(record['region'], region)
                self.assertEqual(record['media_albums'][0]['source_message_ids'], [100, 101])
                self.assertNotIn(key, ctx.bot_data['progress_state'])
                self.assertEqual(ctx.bot.delete_message.await_count, 3)
                resolved = op._find_application(ctx, 9, -20, 102)
                self.assertEqual(resolved[0], key)
                self.assertIsNone(op._find_application(ctx, 9, -10, 13))

    async def test_delete_requires_confirmation_and_same_operator(self):
        ctx, record, key = self.setup_case(stage='other')
        await op.on_operator_button(self.update(record, 'delete_yes'), ctx)
        ctx.bot.delete_message.assert_not_awaited()
        await op.on_operator_button(self.update(record, 'delete'), ctx)
        ctx.bot.delete_message.assert_not_awaited()
        await op.on_operator_button(self.update(record, 'delete_yes', user=78), ctx)
        ctx.bot.delete_message.assert_not_awaited()
        await op.on_operator_button(self.update(record, 'delete_yes'), ctx)
        self.assertEqual(ctx.bot.delete_message.await_count, 3)
        self.assertFalse(ctx.bot_data['applications'])
        ctx.bot.copy_messages.assert_not_awaited()

    async def test_cancel_restores_progress_and_three_buttons(self):
        ctx, record, key = self.setup_case(stage='incomplete')
        ctx.bot_data['progress_state'] = {key: True}
        await op.on_operator_button(self.update(record, 'delete'), ctx)
        update = self.update(record, 'delete_cancel')
        await op.on_operator_button(update, ctx)
        kb = update.callback_query.edit_message_reply_markup.call_args.kwargs['reply_markup']
        buttons = [b for row in kb.inline_keyboard for b in row]
        self.assertEqual(len(buttons), 3)
        self.assertTrue(any('🟡' in b.text for b in buttons))
        self.assertNotIn('delete_confirmation', record)
        ctx.bot.delete_message.assert_not_awaited()

    async def test_missing_route_never_deletes(self):
        ctx, record, _ = self.setup_case()
        with patch('bot.application_queues.queue_group', return_value=''):
            await op.on_operator_button(self.update(record, 'other'), ctx)
        ctx.bot.delete_message.assert_not_awaited()
        ctx.bot.copy_messages.assert_not_awaited()

    async def test_partial_copy_rolls_back_only_destination(self):
        ctx, record, _ = self.setup_case()
        ctx.bot.copy_messages.return_value = [N(message_id=100)]
        with patch('bot.application_queues.queue_group', return_value='-20'):
            await op.on_operator_button(self.update(record, 'incomplete'), ctx)
        self.assertEqual(record['group_chat_id'], -10)
        ctx.bot.delete_message.assert_awaited_once_with(chat_id='-20', message_id=100)

    async def test_info_copy_failure_preserves_source(self):
        ctx, record, _ = self.setup_case()
        ctx.bot.copy_message.side_effect = RuntimeError('permission denied')
        with patch('bot.application_queues.queue_group', return_value='-20'):
            await op.on_operator_button(self.update(record, 'other'), ctx)
        self.assertEqual(record['group_chat_id'], -10)
        self.assertTrue(all(c.kwargs['chat_id'] == '-20' for c in ctx.bot.delete_message.await_args_list))

    async def test_failed_cleanup_retries_without_duplicate_transfer(self):
        ctx, record, _ = self.setup_case()
        update = self.update(record, 'other')
        ctx.bot.delete_message.side_effect = RuntimeError('permission denied')
        with patch('bot.application_queues.queue_group', return_value='-20'):
            await op.on_operator_button(update, ctx)
            self.assertIn('queue_cleanup', record)
            ctx.bot.delete_message.side_effect = None
            await op.on_operator_button(update, ctx)
        ctx.bot.copy_messages.assert_awaited_once()
        self.assertNotIn('queue_cleanup', record)

    async def test_same_user_other_region_remains_after_delete(self):
        ctx, record, _ = self.setup_case(stage='incomplete')
        other_key = op.register_application(ctx, applicant_id=9, region='tashkent', kind='driver', group_chat_id=-30, photo_msg_ids=[31], kb_msg_id=32)
        await op.on_operator_button(self.update(record, 'delete'), ctx)
        await op.on_operator_button(self.update(record, 'delete_yes'), ctx)
        self.assertIn(other_key, ctx.bot_data['applications'])

    async def test_progress_preserves_secondary_buttons(self):
        for stage in ('main', 'incomplete', 'other'):
            ctx, record, key = self.setup_case(stage=stage)
            update = self.update(record, 'progress')
            await op.on_operator_button(update, ctx)
            kb = update.callback_query.edit_message_reply_markup.call_args.kwargs['reply_markup']
            actions = {b.callback_data.split(':')[1] for row in kb.inline_keyboard for b in row}
            self.assertEqual(actions, {'ready','comment','incomplete','other','progress'} if stage == 'main' else {'ready','delete','progress'})

    async def test_secondary_ready_uses_original_region_archive(self):
        for region in ('namangan','tashkent'):
            for stage in ('incomplete','other'):
                ctx, record, key = self.setup_case(region, stage)
                with patch.object(op, 'archive_group', return_value='-40') as route, patch.object(op, '_archive_application', new=AsyncMock(return_value=True)):
                    await op.on_operator_button(self.update(record, 'ready'), ctx)
                route.assert_called_once_with(region)
                self.assertFalse(ctx.bot_data['applications'])

    async def test_main_delete_is_refused_and_comment_stays(self):
        ctx, record, _ = self.setup_case()
        await op.on_operator_button(self.update(record, 'delete'), ctx)
        ctx.bot.delete_message.assert_not_awaited()
        await op.on_operator_button(self.update(record, 'comment'), ctx)
        self.assertTrue(ctx.bot_data['pending_comments'])

    async def test_move_then_real_archive_preserves_album_and_strips_controls(self):
        ctx, record, key = self.setup_case('tashkent')
        ctx.bot.send_media_group = AsyncMock(return_value=[N(message_id=201, media_group_id='album'), N(message_id=202, media_group_id='album')])
        with patch('bot.application_queues.queue_group', return_value='-20'):
            await op.on_operator_button(self.update(record, 'incomplete'), ctx)
        with patch.object(op, 'archive_group', return_value='-40'):
            await op.on_operator_button(self.update(record, 'ready'), ctx)
        ctx.bot.send_media_group.assert_awaited_once()
        self.assertEqual(ctx.bot.send_media_group.call_args.kwargs['chat_id'], '-40')
        self.assertNotIn('reply_markup', ctx.bot.copy_message.call_args.kwargs)
        self.assertFalse(ctx.bot_data['applications'])

    async def test_archive_cleanup_retry_never_archives_twice(self):
        ctx, record, key = self.setup_case(stage='other')
        ctx.bot.delete_message.side_effect = RuntimeError('no delete permission')
        with patch.object(op, 'archive_group', return_value='-40'), patch.object(op, '_archive_application', new=AsyncMock(return_value=True)) as archive:
            update = self.update(record, 'ready')
            await op.on_operator_button(update, ctx)
            self.assertIn('queue_cleanup', record)
            ctx.bot.delete_message.side_effect = None
            await op.on_operator_button(update, ctx)
            archive.assert_awaited_once()
        self.assertFalse(ctx.bot_data['applications'])

    async def test_ready_cannot_run_during_queue_copy(self):
        import asyncio
        ctx, record, key = self.setup_case()
        started, resume = asyncio.Event(), asyncio.Event()
        async def copying(**kwargs):
            started.set()
            await resume.wait()
            return [N(message_id=100), N(message_id=101)]
        ctx.bot.copy_messages.side_effect = copying
        with patch('bot.application_queues.queue_group', return_value='-20'), patch.object(op, '_archive_application', new=AsyncMock(return_value=True)) as archive:
            task = asyncio.create_task(op.on_operator_button(self.update(record, 'other'), ctx))
            await started.wait()
            await op.on_operator_button(self.update(record, 'ready'), ctx)
            archive.assert_not_awaited()
            resume.set()
            await task

    async def test_queue_cannot_run_during_archive_copy(self):
        ctx, record, key = self.setup_case()
        op._ARCHIVES_IN_FLIGHT.add(key)
        try:
            await op.on_operator_button(self.update(record, 'other'), ctx)
            ctx.bot.copy_messages.assert_not_awaited()
        finally:
            op._ARCHIVES_IN_FLIGHT.discard(key)

    async def test_failed_progress_edit_remains_retryable(self):
        ctx, record, key = self.setup_case()
        update = self.update(record, 'progress')
        update.callback_query.edit_message_reply_markup.side_effect = RuntimeError('network')
        await op.on_operator_button(update, ctx)
        self.assertFalse(ctx.bot_data['progress_state'].get(key, False))
        update.callback_query.edit_message_reply_markup.side_effect = None
        await op.on_operator_button(update, ctx)
        self.assertTrue(ctx.bot_data['progress_state'][key])

    async def test_legacy_record_delete_does_not_reappear(self):
        ctx, record, key = self.setup_case(stage='other')
        ctx.bot_data['applications'].clear()
        ctx.bot_data['app_messages'] = {9: {
            'group_chat_id': -10, 'kb_msg_id': 13, 'photo_msg_ids': [11, 12],
            'queue_stage': 'other', 'region': 'namangan',
        }}
        update = self.update(record, 'delete')
        await op.on_operator_button(update, ctx)
        update.callback_query.data = 'op:delete_yes:9'
        await op.on_operator_button(update, ctx)
        self.assertFalse(ctx.bot_data['applications'])
        self.assertFalse(ctx.bot_data['app_messages'])
        self.assertIsNone(op._find_application(ctx, 9, -10, 13))

    def test_routes_never_fall_back_between_regions(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'PERSIST_DIR':directory, 'NAMANGAN_OTHER_PARK_GROUP':'-41', 'TASHKENT_OTHER_PARK_GROUP':''}):
            self.assertEqual(regions.queue_group('namangan','other'), '-41')
            self.assertEqual(regions.queue_group('tashkent','other'), '')
            save_settings({'TASHKENT_CHALA_RASM_GROUP':'-42'})
            self.assertEqual(regions.queue_group('tashkent','incomplete'), '-42')
