import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import httpx

from bot.keyboards.inline import get_start_keyboard

# Specific httpx exceptions for clearer error handling
HTTPX_EXCEPTIONS = (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError)

logger = logging.getLogger(__name__)
router = Router()

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command by registering the user and presenting the welcome dashboard."""
    telegram_id = message.from_user.id
    logger.info(f"Start command triggered by user {telegram_id}")

    # Register user in database via backend API
    try:
        async with httpx.AsyncClient(headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")}) as client:
            resp = await client.post(
                f"{BACKEND_INTERNAL_URL}/api/v1/users/register",
                json={"telegram_id": telegram_id},
                timeout=5.0,
            )
            if resp.status_code == 200:
                status_txt = "✅ Profile synced!"
            else:
                status_txt = "⚠️ API Status Warning"
                logger.warning(f"Registration failed: {resp.text}")
    except HTTPX_EXCEPTIONS as e:
        logger.error(f"Network error calling registration API: {e}")
        status_txt = "⚠️ Local sync active (network offline)"
    except Exception as e:
        logger.critical(f"Unexpected error in registration API call: {e}", exc_info=True)
        status_txt = "⚠️ Something went wrong"

    welcome_text = (
        "👋 <b>Welcome to EmailAgg!</b>\n\n"
        "I am your unified email command center bot. I will aggregate and alert you instantly "
        "on incoming emails from all your connected mailboxes.\n\n"
        f"Profile: {status_txt}\n\n"
        "Use the buttons below to connect your first inbox or query the list of commands."
    )

    await message.answer(welcome_text, reply_markup=get_start_keyboard())


@router.callback_query(F.data == "btn_connect")
async def cb_connect(callback: CallbackQuery):
    """Callback redirect to connect workflow."""
    from bot.handlers.connect import show_connect_message

    await show_connect_message(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "btn_help")
async def cb_help(callback: CallbackQuery):
    """Callback redirect to help descriptions."""
    from bot.handlers.help import show_help_message

    await show_help_message(callback.message)
    await callback.answer()
