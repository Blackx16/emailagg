import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder


def is_valid_webapp_url(url: str) -> bool:
    """Telegram WebApp URLs must be HTTPS, or HTTP localhost/127.0.0.1 for desktop testing."""
    return url.startswith("https://") or "localhost" in url or "127.0.0.1" in url or "lvh.me" in url


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Generate the inline keyboard shown on /start welcome message."""
    frontend_url = os.getenv("FRONTEND_URL", "http://lvh.me:3000")
    builder = InlineKeyboardBuilder()

    if is_valid_webapp_url(frontend_url):
        dash_btn = InlineKeyboardButton(text="🌐 Open Dashboard", web_app=WebAppInfo(url=frontend_url))
    else:
        dash_btn = InlineKeyboardButton(text="🌐 Open Dashboard", url=frontend_url)

    builder.row(
        dash_btn,
        InlineKeyboardButton(text="❓ Help & Commands", callback_data="btn_help"),
    )
    return builder.as_markup()


def get_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Generate inline button to open the dashboard Web App."""
    frontend_url = os.getenv("FRONTEND_URL", "http://lvh.me:3000")
    builder = InlineKeyboardBuilder()

    if is_valid_webapp_url(frontend_url):
        dash_btn = InlineKeyboardButton(text="🌐 Open Dashboard", web_app=WebAppInfo(url=frontend_url))
    else:
        dash_btn = InlineKeyboardButton(text="🌐 Open Dashboard", url=frontend_url)

    builder.row(dash_btn)
    return builder.as_markup()


def get_connect_keyboard(telegram_id: int, backend_url: str) -> InlineKeyboardMarkup:
    """Generate inline buttons containing Microsoft & Google OAuth redirection links."""
    frontend_url = os.getenv("FRONTEND_URL", "http://lvh.me:3000")
    builder = InlineKeyboardBuilder()

    # OAuth authorization endpoints on the backend API
    # Since these are loaded in the browser, backend_url is the public URL
    outlook_url = f"{backend_url}/api/v1/auth/microsoft/login?telegram_id={telegram_id}"
    gmail_url = f"{backend_url}/api/v1/auth/google/login?telegram_id={telegram_id}"

    builder.row(
        InlineKeyboardButton(text="📬 Connect Outlook", url=outlook_url),
        InlineKeyboardButton(text="📨 Connect Gmail", url=gmail_url),
    )

    if is_valid_webapp_url(frontend_url):
        dash_btn = InlineKeyboardButton(text="🌐 Open Web Dashboard", web_app=WebAppInfo(url=frontend_url))
    else:
        dash_btn = InlineKeyboardButton(text="🌐 Open Web Dashboard", url=frontend_url)

    builder.row(dash_btn)
    return builder.as_markup()
