import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, WebAppInfo
import httpx

from bot.keyboards.inline import is_valid_webapp_url

logger = logging.getLogger(__name__)
router = Router()

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Human-readable plan display names and emoji
PLAN_DISPLAY = {
    "free": ("🆓", "Free"),
    "pro": ("⭐", "Pro"),
    "agency": ("🏢", "Agency"),
}


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command to show user profile and plan information."""
    telegram_id = message.from_user.id
    logger.info(f"Settings command triggered by user {telegram_id}")

    # Fetch user profile
    user_data = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BACKEND_INTERNAL_URL}/api/v1/users/profile",
                params={"telegram_id": telegram_id},
                timeout=5.0,
            )

            if resp.status_code == 404:
                await message.answer(
                    "❌ <b>Profile not found.</b>\nPlease send /start first to register your profile."
                )
                return

            if resp.status_code != 200:
                logger.error(f"Failed to fetch user profile: {resp.text}")
                await message.answer("⚠️ Failed to load your profile. Please try again later.")
                return

            user_data = resp.json()

    except Exception as e:
        logger.error(f"Error connecting to backend API: {e}")
        await message.answer("⚠️ Connection to database offline. Please try again later.")
        return

    # Extract user info
    plan = user_data.get("plan", "free")
    max_accounts = user_data.get("max_accounts", 3)
    connected_accounts = user_data.get("connected_accounts", 0)
    active_accounts = user_data.get("active_accounts", 0)

    plan_emoji, plan_name = PLAN_DISPLAY.get(plan, ("📋", plan.capitalize()))

    # Build usage bar
    usage_pct = (active_accounts / max_accounts * 100) if max_accounts > 0 else 0
    filled = round(usage_pct / 10)
    bar = "▓" * filled + "░" * (10 - filled)

    text = (
        f"⚙️ <b>Your Settings & Profile</b>\n\n"
        f"<b>Plan:</b> {plan_emoji} {plan_name}\n"
        f"<b>Account Limit:</b> {max_accounts} mailboxes\n"
        f"<b>Connected:</b> {active_accounts} / {max_accounts} active\n"
        f"<b>Usage:</b> [{bar}] {usage_pct:.0f}%\n\n"
    )

    if active_accounts >= max_accounts:
        text += (
            "⚠️ <i>You've reached your account limit. "
            "Upgrade your plan or disconnect an unused account.</i>\n\n"
        )
    elif active_accounts >= max_accounts * 0.8:
        text += (
            "💡 <i>You're approaching your account limit. "
            "Consider upgrading for more capacity.</i>\n\n"
        )

    text += "Manage your accounts, filters, and billing from the web dashboard."

    # Build keyboard
    builder = InlineKeyboardBuilder()

    if is_valid_webapp_url(FRONTEND_URL):
        dash_btn = InlineKeyboardButton(
            text="🌐 Open Web Dashboard", web_app=WebAppInfo(url=FRONTEND_URL)
        )
    else:
        dash_btn = InlineKeyboardButton(text="🌐 Open Web Dashboard", url=FRONTEND_URL)

    builder.row(dash_btn)
    builder.row(
        InlineKeyboardButton(text="📧 View Accounts", callback_data="btn_accounts"),
        InlineKeyboardButton(text="🔌 Disconnect", callback_data="btn_disconnect"),
    )

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "btn_accounts")
async def cb_accounts(callback: CallbackQuery):
    """Callback redirect to accounts listing."""
    from bot.handlers.accounts import cmd_accounts

    await cmd_accounts(callback.message)
    await callback.answer()


@router.callback_query(F.data == "btn_disconnect")
async def cb_disconnect(callback: CallbackQuery):
    """Callback redirect to disconnect workflow."""
    from bot.handlers.disconnect import cmd_disconnect

    await cmd_disconnect(callback.message)
    await callback.answer()

