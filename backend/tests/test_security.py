import pytest
import time
import hmac
import hashlib
from fastapi import HTTPException
from app.core.security import verify_telegram_init_data, verify_internal
from app.core.config import settings

def test_verify_telegram_init_data_freshness():
    bot_token = "test_bot_token"
    # Create valid payload but old auth_date
    auth_date = int(time.time()) - 86401 # 24 hours and 1 second ago
    
    # Construct check string and hash manually
    params = {"query_id": "test", "auth_date": str(auth_date)}
    sorted_params = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_params)
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    init_data = f"query_id=test&auth_date={auth_date}&hash={calc_hash}"
    
    assert verify_telegram_init_data(init_data, bot_token) is None, "Expected None due to freshness check failure"

def test_verify_telegram_init_data_valid():
    bot_token = "test_bot_token"
    auth_date = int(time.time()) - 10 # 10 seconds ago
    
    params = {"query_id": "test", "auth_date": str(auth_date)}
    sorted_params = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_params)
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    init_data = f"query_id=test&auth_date={auth_date}&hash={calc_hash}"
    
    result = verify_telegram_init_data(init_data, bot_token)
    assert result is not None
    assert result["query_id"] == "test"

@pytest.mark.asyncio
async def test_verify_internal_success():
    settings.INTERNAL_API_KEY = "test_internal_key"
    # Should not raise exception
    await verify_internal(x_internal_key="test_internal_key")

@pytest.mark.asyncio
async def test_verify_internal_failure():
    settings.INTERNAL_API_KEY = "test_internal_key"
    with pytest.raises(HTTPException) as excinfo:
        await verify_internal(x_internal_key="wrong_key")
    assert excinfo.value.status_code == 403
