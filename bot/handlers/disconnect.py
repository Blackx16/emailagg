import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import httpx

logger = logging.getLogger(__name__)
router = Router()

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")


@router.message(Command("disconnect"))
async def cmd_disconnect(message: Message):
    """Handle /disconnect command to show connected accounts with disconnect buttons."""
    telegram_id = message.from_user.id
    logger.info(f"Disconnect command triggered by user {telegram_id}")

    try:
        async with httpx.AsyncClient(headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")}) as client:
            resp = await client.get(
                f"{BACKEND_INTERNAL_URL}/api/v1/accounts/internal/by-telegram/{telegram_id}",
                timeout=5.0,
            )

            if resp.status_code == 404:
                await message.answer(
                    "❌ <b>Profile not found.</b>\nPlease send /start first to register your profile."
                )
                return

            if resp.status_code != 200:
                logger.error(f"Failed to query accounts: {resp.text}")
                await message.answer("⚠️ Failed to load your accounts. Please try again later.")
                return

            accounts = resp.json()

    except Exception as e:
        logger.error(f"Error connecting to backend API: {e}")
        await message.answer("⚠️ Connection to database offline. Please try again later.")
        return

    # Filter to only active/syncing/error accounts (not already disconnected)
    active_accounts = [a for a in accounts if a.get("status") != "disconnected"]

    if not active_accounts:
        await message.answer(
            "🔌 <b>Disconnect Account</b>\n\n"
            "You don't have any active connected accounts.\n\n"
            "Use /connect to add a mailbox first."
        )
        return

    text = (
        "🔌 <b>Disconnect an Account</b>\n\n"
        "Select an account below to disconnect it. "
        "This will revoke access tokens and stop syncing.\n"
    )

    builder = InlineKeyboardBuilder()
    for acc in active_accounts:
        email = acc["email"]
        provider = acc["provider"].capitalize()
        status = acc["status"]

        # Status indicator
        if status == "active":
            icon = "✅"
        elif status == "syncing":
            icon = "🔄"
        elif status == "error":
            icon = "⚠️"
        else:
            icon = "📧"

        btn_text = f"{icon} {email} ({provider})"
        callback_data = f"disconnect:{acc['id']}"
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=callback_data))

    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="disconnect:cancel"))

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "disconnect:cancel")
async def cb_disconnect_cancel(callback: CallbackQuery):
    """Handle cancel button on disconnect menu."""
    await callback.message.edit_text("👍 Disconnect cancelled. No accounts were changed.")
    await callback.answer()


@router.callback_query(F.data.startswith("disconnect:"))
async def cb_disconnect_account(callback: CallbackQuery):
    """Handle disconnect button click to actually disconnect an account."""
    account_id = callback.data.split(":", 1)[1]
    telegram_id = callback.from_user.id
    logger.info(f"Disconnect callback for account {account_id} by user {telegram_id}")

    try:
        async with httpx.AsyncClient(headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")}) as client:
            resp = await client.post(
                f"{BACKEND_INTERNAL_URL}/api/v1/accounts/{account_id}/disconnect",
                params={"telegram_id": telegram_id},
                timeout=5.0,
            )

            if resp.status_code == 200:
                result = resp.json()
                email = result.get("email", "Unknown")
                await callback.message.edit_text(
                    f"✅ <b>Account Disconnected</b>\n\n"
                    f"<b>{email}</b> has been disconnected successfully.\n"
                    f"Access tokens have been revoked and syncing has stopped.\n\n"
                    f"Use /connect to reconnect this or another account."
                )
            elif resp.status_code == 404:
                await callback.message.edit_text(
                    "❌ Account not found or you don't have permission to disconnect it."
                )
            elif resp.status_code == 400:
                detail = resp.json().get("detail", "Invalid request.")
                await callback.message.edit_text(f"⚠️ {detail}")
            else:
                logger.error(f"Disconnect failed: {resp.text}")
                await callback.message.edit_text(
                    "⚠️ Failed to disconnect the account. Please try again later."
                )

    except Exception as e:
        logger.error(f"Error calling disconnect API: {e}")
        await callback.message.edit_text(
            "⚠️ Connection to database offline. Please try again later."
        )

    await callback.answer()
