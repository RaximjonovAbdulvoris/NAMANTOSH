"""Run `python -m bot.configure tashkent` in Windows CMD or a Linux terminal."""
import argparse
import asyncio
import logging
import os

from bot.route_settings import (
    TASHKENT_KEYS, destination, read_settings, save_settings, settings_path, validate,
)

LABELS = {
    "driver1": "Haydovchi 1-guruh",
    "driver2": "Haydovchi 2-guruh (ixtiyoriy; o'chirish uchun none)",
    "brand": "Brend guruhi",
    "spectre": "Spectre Energy guruhi",
    "archive": "Arxiv guruhi",
}


async def check_routes() -> int:
    """Read-only Telegram checks; never poll, send applications or reveal tokens."""
    from telegram import Bot
    from telegram.error import InvalidToken, TelegramError

    logging.getLogger("httpx").setLevel(logging.WARNING)
    routes = {name: destination(key) for name, key in TASHKENT_KEYS.items()}
    failures = 0
    for name, value in routes.items():
        if not value and name == "driver2":
            continue
        try:
            validate(TASHKENT_KEYS[name], value)
        except ValueError as exc:
            print(exc)
            failures += 1
    if failures:
        return 1
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN sozlanmagan. Tokenni xavfsiz muhit sozlamasida kiriting.")
        return 1
    try:
        async with Bot(token=token) as bot:
            for name, value in routes.items():
                if not value:
                    continue
                try:
                    chat = await bot.get_chat(int(value))
                    member = await bot.get_chat_member(chat.id, bot.id)
                    if chat.type not in ("group", "supergroup"):
                        raise ValueError("ID guruhga tegishli emas.")
                    if member.status not in ("administrator", "creator"):
                        raise ValueError("Botni guruh administratori qiling.")
                    if name != "archive" and member.status != "creator" and not getattr(
                        member, "can_delete_messages", False
                    ):
                        raise ValueError("Botga xabarlarni o'chirish ruxsatini bering.")
                    print(f"{TASHKENT_KEYS[name]}: OK")
                except ValueError as exc:
                    print(f"{TASHKENT_KEYS[name]}: {exc}")
                    failures += 1
                except TelegramError as exc:
                    print(f"{TASHKENT_KEYS[name]}: {type(exc).__name__}; ID va bot ruxsatlarini tekshiring.")
                    failures += 1
            try:
                channel_member = await bot.get_chat_member("@WB_HUMO_TAXI", bot.id)
                if channel_member.status not in ("administrator", "creator"):
                    raise ValueError("Bot obuna kanalida administrator emas.")
                print("@WB_HUMO_TAXI obuna tekshiruvi: OK")
            except (TelegramError, ValueError):
                print("@WB_HUMO_TAXI: botni kanal administratori qiling.")
                failures += 1
    except InvalidToken:
        print("Telegram tokenni qabul qilmadi. TELEGRAM_BOT_TOKEN ni xavfsiz sozlamada yangilang.")
        return 1
    except TelegramError as exc:
        print(f"Telegram ulanish xatosi: {type(exc).__name__}.")
        return 1
    return 1 if failures else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Toshkent guruhlarini terminaldan sozlash.")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("tashkent", help="IDlarni kiritish yoki o'zgartirish")
    for name in TASHKENT_KEYS:
        setup.add_argument(f"--{name}", help=LABELS[name])
    commands.add_parser("show", help="Amaldagi IDlar va ularning manbasini ko'rish")
    commands.add_parser("check", help="Token, guruhlar va bot ruxsatlarini tekshirish")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return asyncio.run(check_routes())
        if args.command == "show":
            local = read_settings()
            print(f"Sozlama fayli: {settings_path()}")
            for name, key in TASHKENT_KEYS.items():
                source = "CMD/fayl" if key in local else "muhit"
                print(f"{key}: {destination(key) or 'sozlanmagan'} ({source})")
            return 0
        changes = {
            key: getattr(args, name) for name, key in TASHKENT_KEYS.items()
            if getattr(args, name) is not None
        }
        if not changes:
            print("Mavjud IDni saqlash uchun Enter bosing. Token kiritmang.")
            for name, key in TASHKENT_KEYS.items():
                current = destination(key)
                answer = input(f"{LABELS[name]} [{current or 'sozlanmagan'}]: ").strip()
                changes[key] = answer or current
        for key, value in changes.items():
            if key == TASHKENT_KEYS["driver2"] and value.lower() == "none":
                changes[key] = ""
        # Validate the complete effective setup before saving any change.
        for name, key in TASHKENT_KEYS.items():
            validate(key, changes.get(key, destination(key)))
        save_settings(changes)
        print(f"Saqlandi: {settings_path()}")
        print("Bu IDlar muhit sozlamalaridan ustun. Bot shu kompyuterda ishlashi kerak.")
        print("Tekshirish: python -m bot.configure check")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Sozlash xatosi: {exc}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nBekor qilindi; IDlar o'zgartirilmadi.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())