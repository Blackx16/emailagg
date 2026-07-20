import logging
import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = Router()

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")


@router.message(Command("accounts"))
async def cmd_accounts(message: Message, telegram_id: int = None):
    """Handle /accounts command to list all connected mailboxes and their states."""
    telegram_id = telegram_id or message.chat.id
    logger.info(f"Accounts query triggered by user {telegram_id}")

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

    if not accounts:
        await message.answer(
            "📧 <b>Connected Accounts</b>\n\n"
            "You haven't connected any email accounts yet!\n\n"
            "Use /connect to add your first mailbox."
        )
        return

    text = "📧 <b>Your Connected Accounts</b>\n\n"
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        provider = acc["provider"].capitalize()
        status = acc["status"]
        last_sync_str = acc.get("last_sync")
        error_msg = acc.get("error_message")

        # Status emoji formatting
        if status == "active":
            status_desc = "✅ Active"
        elif status == "syncing":
            status_desc = "🔄 Syncing"
        elif status == "error":
            status_desc = f"⚠️ Syncing Failed"
        elif status == "disconnected":
            status_desc = "💤 Disconnected"
        else:
            status_desc = status.capitalize()

        # Format last sync time human-readably
        time_desc = "Never synced"
        if last_sync_str:
            try:
                last_sync = datetime.fromisoformat(last_sync_str.replace("Z", "+00:00"))
                diff = datetime.now(timezone.utc) - last_sync
                if diff.total_seconds() < 60:
                    time_desc = "Just now"
                elif diff.total_seconds() < 3600:
                    mins = int(diff.total_seconds() / 60)
                    time_desc = f"{mins}m ago"
                elif diff.total_seconds() < 86400:
                    hours = int(diff.total_seconds() / 3600)
                    time_desc = f"{hours}h ago"
                else:
                    time_desc = last_sync.strftime("%d %b, %H:%M")
            except Exception:
                time_desc = "Recent"

        block = f"{i}. <b>{email}</b> ({provider})\n"
        block += f"   Status: {status_desc}\n"
        block += f"   Last Sync: {time_desc}\n"
        if status == "error" and error_msg:
            block += f"   <i>Error: {error_msg}</i>\n"
        block += "\n"

        if len(text) + len(block) > 4000:
            await message.answer(text)
            text = ""
        text += block

    suffix = "Use /connect to link a new mailbox."
    if len(text) + len(suffix) > 4000:
        await message.answer(text)
        text = suffix
    else:
        text += suffix

    await message.answer(text)
