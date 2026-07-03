import logging
import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, WebAppInfo
import httpx

from bot.keyboards.inline import is_valid_webapp_url

logger = logging.getLogger(__name__)
router = Router()

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    """Handle /rules command to show active forwarding rules and counts."""
    telegram_id = message.from_user.id
    logger.info(f"Rules command triggered by user {telegram_id}")

    try:
        async with httpx.AsyncClient(headers={"X-Internal-Key": os.getenv("INTERNAL_API_KEY", "")}) as client:
            resp = await client.get(
                f"{BACKEND_INTERNAL_URL}/api/v1/rules/internal/by-telegram/{telegram_id}",
                timeout=5.0,
            )

            if resp.status_code == 404:
                await message.answer(
                    "❌ <b>Profile not found.</b>\nPlease send /start first to register your profile."
                )
                return

            if resp.status_code != 200:
                logger.error(f"Failed to query rules: {resp.text}")
                await message.answer("⚠️ Failed to load your forwarding rules. Please try again later.")
                return

            rules = resp.json()

    except Exception as e:
        logger.error(f"Error connecting to backend API: {e}")
        await message.answer("⚠️ Connection to database offline. Please try again later.")
        return

    total_count = len(rules)
    active_count = sum(1 for r in rules if r.get("is_active", False))

    text = "📋 <b>Email Forwarding Rules</b>\n\n"
    text += f"You have <b>{active_count} active</b> / <b>{total_count} total</b> rules configured.\n\n"

    if not rules:
        text += (
            "You haven't created any forwarding rules yet.\n\n"
            "Rules allow you to filter incoming emails (by subject, sender, or content) "
            "and automatically forward them to another email address via SMTP."
        )
    else:
        text += "<b>Current Rules:</b>\n\n"
        # List up to 5 rules to prevent spamming chat
        for i, rule in enumerate(rules[:5], 1):
            status = "🟢" if rule.get("is_active") else "⚫"
            scope = "Global" if not rule.get("mail_account_id") else "Specific Account"
            forward_to = rule.get("forward_to_email")

            conds = []
            if rule.get("condition_subject_contains"):
                conds.append(f"Subject ~ '{rule['condition_subject_contains']}'")
            if rule.get("condition_from_domain"):
                conds.append(f"From domain @{rule['condition_from_domain']}")
            if rule.get("condition_from_email"):
                conds.append(f"From '{rule['condition_from_email']}'")
            if rule.get("condition_body_contains"):
                conds.append(f"Body ~ '{rule['condition_body_contains']}'")

            cond_str = " AND ".join(conds) if conds else "Any Email"
            text += f"{i}. {status} <b>{scope}</b> → <code>{forward_to}</code>\n   <i>Filter: {cond_str}</i>\n\n"

        if total_count > 5:
            text += f"<i>...and {total_count - 5} more rules.</i>\n\n"

        text += "Use the web dashboard to create, edit, or toggle rules."

    # Build keyboard with a direct link to rules tab
    rules_tab_url = f"{FRONTEND_URL}?tab=rules"
    builder = InlineKeyboardBuilder()

    if is_valid_webapp_url(FRONTEND_URL):
        dash_btn = InlineKeyboardButton(
            text="📋 Manage Rules", web_app=WebAppInfo(url=rules_tab_url)
        )
    else:
        dash_btn = InlineKeyboardButton(text="📋 Manage Rules", url=rules_tab_url)

    builder.row(dash_btn)
    await message.answer(text, reply_markup=builder.as_markup())
