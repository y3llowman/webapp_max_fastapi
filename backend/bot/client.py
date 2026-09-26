"""Общий клиент MAX: им шлют сообщения и бот, и API (документ в чат), и планировщик.
bot/sender.py — остаток от Telegram, не использовать."""
from maxapi import Bot
from maxapi.enums.parse_mode import ParseMode
from maxapi.types.attachments.attachment import ButtonsPayload

from core.env import ENV

bot = Bot(token=ENV.MAX_BOT_TOKEN.get_secret_value())

_bot_id: int | None = None


async def bot_id() -> int:
    """id бота — для кнопки open_app, которая открывает его мини-приложение."""
    global _bot_id
    if _bot_id is None:
        _bot_id = (await bot.get_me()).user_id
    return _bot_id


async def send_html(max_user_id: int, text: str, keyboard: dict | None = None) -> str | None:
    """Сообщение пользователю; keyboard — inline_keyboard в формате radar.render.keyboard()."""
    attachments = [ButtonsPayload.model_validate(keyboard["payload"]).pack()] if keyboard else None
    sent = await bot.send_message(user_id=max_user_id, text=text, format=ParseMode.HTML,
                                  attachments=attachments)
    return sent.message.body.mid if sent else None
