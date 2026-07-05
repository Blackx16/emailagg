import httpx
import sys
import time
import uuid
import hmac
import hashlib
from app.core.config import settings

def _generate_valid_init_data(telegram_id: int, username: str) -> str:
    auth_date = int(time.time())
    params = {
        "user": f'{{"id":{telegram_id},"username":"{username}"}}',
        "auth_date": str(auth_date)
    }
    sorted_params = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_params)
    secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return f"user={params['user']}&auth_date={auth_date}&hash={calc_hash}"

def test_login_rate_limiting():
    print("--- Testing Telegram Login Rate Limiting ---")
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/v1/auth/telegram/login"
    
    # We will make up to 50 requests. The limit is 20/minute.
    # Since Uvicorn runs 2 workers, requests are load balanced. 50 requests guarantees 429 triggers.
    got_429 = False
    init_data = _generate_valid_init_data(12345, "rate_limit_test")
    
    print("Sending concurrent login requests to trigger rate limit (20/min)...")
    for i in range(1, 51):
        try:
            resp = httpx.post(login_url, json={"initData": init_data}, timeout=5.0)
            if resp.status_code == 429:
                got_429 = True
                print(f"Request {i}: Successfully triggered 429 Too Many Requests rate limit!")
                break
            elif resp.status_code == 200:
                pass
            else:
                print(f"Request {i}: Got unexpected status {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Request {i}: Connection error: {e}")
            break
            
    assert got_429 is True, "Expected to trigger 429 rate limit but did not!"
    print("✅ Telegram login rate limiting test passed successfully!")


def test_rules_crud():
    print("\n--- Testing Forwarding Rules CRUD ---")
    base_url = "http://localhost:8000"
    telegram_id = 88812345
    
    init_data = _generate_valid_init_data(telegram_id, "crud_test")
    login_url = f"{base_url}/api/v1/auth/telegram/login"
    
    print("Logging in to get token...")
    try:
        resp = httpx.post(login_url, json={"initData": init_data}, timeout=5.0)
        if resp.status_code == 429:
            print("Already rate-limited. Waiting 30s to clear rate limits...")
            time.sleep(30)
            resp = httpx.post(login_url, json={"initData": init_data}, timeout=5.0)
            
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            sys.exit(1)
            
        token = resp.json()["access_token"]
        print("Login successful! Got token.")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {token}"}
    rules_url = f"{base_url}/api/v1/rules"
    
    # 2. Get Rules (should be empty initially)
    resp = httpx.get(rules_url, headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    rules = resp.json()
    print(f"Initial rules count: {len(rules)}")
    
    # 3. Create Rule
    new_rule_payload = {
        "condition_subject_contains": "Netflix Verification",
        "condition_from_domain": "netflix.com",
        "forward_to_email": "forward-target@lvh.me",
        "is_active": True
    }
    resp = httpx.post(rules_url, json=new_rule_payload, headers=headers)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    created_rule = resp.json()
    rule_id = created_rule["id"]
    print(f"Rule created successfully with ID: {rule_id}")
    assert created_rule["condition_subject_contains"] == "Netflix Verification"
    assert created_rule["condition_from_domain"] == "netflix.com"
    assert created_rule["forward_to_email"] == "forward-target@lvh.me"
    assert created_rule["is_active"] is True
    
    # 4. Read Rules (should have 1 rule)
    resp = httpx.get(rules_url, headers=headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 1, f"Expected 1 rule, got {len(rules)}"
    print(f"Rules list contains newly created rule: {rules[0]['id']}")
    
    # 5. Update Rule
    update_payload = {
        "condition_subject_contains": "Updated Subject",
        "condition_from_domain": "netflix.com",
        "forward_to_email": "updated-target@lvh.me",
        "is_active": False
    }
    resp = httpx.put(f"{rules_url}/{rule_id}", json=update_payload, headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    updated_rule = resp.json()
    assert updated_rule["condition_subject_contains"] == "Updated Subject"
    assert updated_rule["forward_to_email"] == "updated-target@lvh.me"
    assert updated_rule["is_active"] is False
    print("Rule updated successfully!")
    
    # 6. Delete Rule
    resp = httpx.delete(f"{rules_url}/{rule_id}", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print("Rule deleted successfully!")
    
    # 7. Read Rules again (should be empty again)
    resp = httpx.get(rules_url, headers=headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 0, f"Expected 0 rules, got {len(rules)}"
    print("✅ Rules CRUD test passed successfully!")


if __name__ == "__main__":
    # Run CRUD test first (before triggering rate limit)
    test_rules_crud()
    # Then run Rate Limit test
    test_login_rate_limiting()
    print("\n🎉 All API integration tests passed successfully!")
