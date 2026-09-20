import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.filters.command import CommandStart
from maxapi.types import MessageCreated

# logger = logging.getLogger(__file__)
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)
logger.setLevel(level=logging.info)

bot = Bot()
dp = Dispatcher()

# Команда /start боту
@dp.message_created(CommandStart())
async def hello(event: MessageCreated):
    await event.message.answer("Привет из вебхука!")


async def main():
    await dp.handle_webhook(
        bot=bot,
        host="0.0.0.0",
        port=8080,
    )

if __name__ == "__main__":
    asyncio.run(main())