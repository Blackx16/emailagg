import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.handlers import start, connect, accounts, help, disconnect, settings, rules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(connect.router)
    dp.include_router(accounts.router)
    dp.include_router(help.router)
    dp.include_router(disconnect.router)
    dp.include_router(settings.router)
    dp.include_router(rules.router)

    logger.info("Setting chat menu button...")
    try:
        from aiogram.types import MenuButtonWebApp, MenuButtonDefault, WebAppInfo
        frontend_url = os.getenv("FRONTEND_URL", "http://lvh.me:3000")
        
        # Check if URL meets Telegram's WebApp requirements (HTTPS or localhost/lvh.me)
        is_valid_webapp = (
            frontend_url.startswith("https://")
            or "localhost" in frontend_url
            or "127.0.0.1" in frontend_url
            or "lvh.me" in frontend_url
        )
        
        if is_valid_webapp:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🌐 Dashboard",
                    web_app=WebAppInfo(url=frontend_url)
                )
            )
            logger.info("Chat menu button set as Web App successfully.")
        else:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonDefault()
            )
            logger.info("Chat menu button set to default (non-HTTPS frontend URL).")
    except Exception as e:
        logger.error(f"Failed to set chat menu button: {e}")

    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
