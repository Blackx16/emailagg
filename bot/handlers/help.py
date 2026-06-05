import logging
import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from bot.keyboards.inline import is_valid_webapp_url

logger = logging.getLogger(__name__)
router = Router()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command to show bot instructions."""
    await show_help_message(message)


async def show_help_message(message: Message):
    """Common logic to display help information and commands."""
    help_text = (
        "❓ <b>EmailAgg Bot Commands & Help</b>\n\n"
        "Here is a list of commands you can use to interact with EmailAgg:\n\n"
        "🚀 <b>Core Commands:</b>\n"
        "/start - Register your profile and view the welcome dashboard\n"
        "🔌 /connect - Connect a new Microsoft Outlook or Google Gmail account\n"
        "📧 /accounts - View connected email accounts and sync states\n"
        "❓ /help - Display this commands help guide\n\n"
        "🌐 <b>Web Dashboard:</b>\n"
        "To read emails, view sync analytics, configure filters, or manage billing subscriptions, "
        "visit your personalized web dashboard."
    )

    # Inline button to open Next.js dashboard
    builder = InlineKeyboardBuilder()
    if is_valid_webapp_url(FRONTEND_URL):
        dash_btn = InlineKeyboardButton(text="👁️ Open Web Dashboard", web_app=WebAppInfo(url=FRONTEND_URL))
    else:
        dash_btn = InlineKeyboardButton(text="👁️ Open Web Dashboard", url=FRONTEND_URL)
        
    builder.row(dash_btn)

    await message.answer(help_text, reply_markup=builder.as_markup())
