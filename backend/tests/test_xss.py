import pytest
from app.api.routes.auth import register_oauth_account
from unittest.mock import patch, MagicMock
from fastapi.responses import HTMLResponse

@pytest.mark.asyncio
async def test_xss_prevention_in_oauth_callback():
    db_mock = MagicMock()
    with patch('app.api.routes.auth.find_or_create_oauth_account', return_value=(1, "123e4567-e89b-12d3-a456-426614174000")), \
         patch('app.api.routes.auth.telemetry.log_event'), \
         patch('app.api.routes.auth.sync_account.delay'), \
         patch('app.api.routes.auth.send_telegram_message'):

        response = await register_oauth_account(
            telegram_id=123,
            provider="<script>alert('xss provider')</script>",
            email="<img src=x onerror=alert('xss email')>",
            access_token="test",
            refresh_token="test",
            expires_in=3600,
            db=db_mock
        )

        assert isinstance(response, HTMLResponse)
        content = response.body.decode()

        # Check that the malicious input is escaped
        assert "<script>" not in content
        assert "&lt;script&gt;alert(&#x27;xss provider&#x27;)&lt;/script&gt;" in content.lower() or "&lt;script&gt;alert(&#x27;xss provider&#x27;)&lt;/script&gt;".capitalize() in content.capitalize()
        assert "<img src=x" not in content
        assert "&lt;img src=x onerror=alert(&#x27;xss email&#x27;)&gt;" in content
