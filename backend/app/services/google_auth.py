import secrets
import urllib.parse
import httpx
from app.core.config import settings
from app.core.redis import get_redis

# OAuth state token TTL (10 minutes)
OAUTH_STATE_TTL = 600


async def get_login_url(telegram_id: int) -> str:
    """Generate the Google OAuth2 authorization URL with a secure state token."""
    redis = await get_redis()
    state_token = secrets.token_urlsafe(32)
    await redis.set(f"oauth_state:{state_token}", str(telegram_id), ex=OAUTH_STATE_TTL)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email",
        "state": state_token,
        "access_type": "offline",
        "prompt": "consent",
    }
    encoded = urllib.parse.urlencode(params)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{encoded}"


async def exchange_code(code: str) -> dict:
    """Exchange the OAuth authorization code for tokens and fetch user email."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise ValueError(f"Google token exchange failed: {resp.text}")

        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Get user's email address
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise ValueError(f"Failed to fetch Google userinfo: {userinfo_resp.text}")

        userinfo = userinfo_resp.json()
        email = userinfo.get("email")
        if not email:
            raise ValueError("Google account did not return a valid email address.")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "email": email.lower(),
        }


async def refresh_tokens(refresh_token: str) -> dict:
    """Refresh the Google access token using the refresh token."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise ValueError(f"Google token refresh failed: {resp.text}")

        token_data = resp.json()
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", 3600),
        }
