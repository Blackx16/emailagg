import logging
import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.keyboards.inline import get_connect_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Public facing URL that the user clicks in their browser
BACKEND_PUBLIC_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@router.message(Command("connect"))
async def cmd_connect(message: Message):
    """Handle /connect command to connect Microsoft Outlook or Google Gmail."""
    await show_connect_message(message, message.from_user.id)


async def show_connect_message(message: Message, telegram_id: int):
    """Common logic to display OAuth connection options."""
    connect_text = (
        "🔌 <b>Connect your Email Mailboxes</b>\n\n"
        "Click one of the buttons below to authenticate your mailbox via a secure login screen.\n\n"
        "🔒 <b>Security Note:</b> We never see or store your raw account passwords. "
        "Everything is secured using encrypted OAuth authorization tokens."
    )

    await message.answer(
        connect_text, reply_markup=get_connect_keyboard(telegram_id, BACKEND_PUBLIC_URL)
    )
