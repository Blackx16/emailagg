import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
import httpx
from app.core.config import settings
from app.core.redis import get_redis

# OAuth state token TTL (10 minutes)
OAUTH_STATE_TTL = 600


async def get_login_url(telegram_id: int) -> str:
    """Generate the Microsoft OAuth2 authorization URL with a secure state token."""
    redis = await get_redis()
    state_token = secrets.token_urlsafe(32)
    await redis.set(f"oauth_state:{state_token}", str(telegram_id), ex=OAUTH_STATE_TTL)

    params = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "response_mode": "query",
        "scope": "offline_access Mail.Read User.Read",
        "state": state_token,
    }
    encoded = urllib.parse.urlencode(params)
    return f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize?{encoded}"


async def exchange_code(code: str) -> dict:
    """Exchange the OAuth authorization code for tokens and fetch user email."""
    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
        "scope": "offline_access Mail.Read User.Read",
    }

    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        # Exchange code for tokens
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise ValueError(f"Microsoft token exchange failed: {resp.text}")

        token_data = resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Get user's profile info (for the email address)
        profile_resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_resp.status_code != 200:
            raise ValueError(f"Failed to fetch Microsoft profile: {profile_resp.text}")

        profile = profile_resp.json()
        email = profile.get("mail") or profile.get("userPrincipalName")
        if not email:
            raise ValueError("Microsoft account did not return a valid email address.")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "email": email.lower(),
        }


async def refresh_tokens(refresh_token: str) -> dict:
    """Refresh the Microsoft access token using the refresh token."""
    token_url = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": settings.MICROSOFT_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "offline_access Mail.Read User.Read",
    }

    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise ValueError(f"Microsoft token refresh failed: {resp.text}")

        token_data = resp.json()
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in", 3600),
        }
