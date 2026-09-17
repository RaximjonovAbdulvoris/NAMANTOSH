"""Shared subscription gate for all application flows."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

REQUIRED_CHANNEL = "@WB_HUMO_TAXI"
CHANNEL_URL = "https://t.me/WB_HUMO_TAXI"


def subscription_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Kanalga obuna bo‘lish", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Tekshirish", callback_data=callback_data)],
    ])


async def is_subscribed(bot, user_id: int) -> bool | None:
    """Return True/False, or None when Telegram could not check membership."""
    try:
        member = await bot.get_chat_member(
            chat_id=REQUIRED_CHANNEL, user_id=user_id
        )
    except TelegramError:
        logger.warning("Required channel membership check failed")
        return None
    return member.status in ("creator", "administrator", "member") or (
        member.status == "restricted" and member.is_member
    )


async def require_subscription(
    update,
    context,
    *,
    callback_data: str,
    error_contact: str = "@WB_HUMO_TAXI",
) -> bool:
    """Gate a form on the shared WB HUMO channel.

    This function never changes user data.  Callers can therefore safely use
    it before collecting the first answer and decide which conversation state
    to return when it is not yet satisfied.
    """
    user = update.effective_user
    joined = await is_subscribed(context.bot, user.id)
    keyboard = subscription_keyboard(callback_data)
    message = update.effective_message

    if joined is None:
        if update.callback_query:
            await update.callback_query.answer()
        await message.reply_text(
            "A’zolikni hozir tekshirib bo‘lmadi. Iltimos, birozdan keyin "
            "«✅ Tekshirish» tugmasini qayta bosing. Muammo davom etsa, "
            f"{error_contact} orqali bog‘laning.",
            reply_markup=keyboard,
        )
        return False

    if not joined:
        query = update.callback_query
        if query:
            await query.answer(
                "Iltimos, avval WB HUMO kanaliga obuna bo‘ling.",
                show_alert=True,
            )
        else:
            await message.reply_text(
                "📢 <b>Ariza yuborish uchun avval WB HUMO kanaliga "
                "obuna bo‘ling.</b>\n\n"
                "1️⃣ «Kanalga obuna bo‘lish» tugmasini bosing.\n"
                "2️⃣ Botga qaytib, «✅ Tekshirish»ni bosing.",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        return False

    if query := update.callback_query:
        await query.answer()
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except TelegramError:
            logger.debug("Could not remove subscription keyboard", exc_info=True)
    return True