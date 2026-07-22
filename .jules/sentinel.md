## 2024-07-06 - Prevented Timing Attack in Telegram Auth Verification
**Vulnerability:** Timing attack possible during Telegram initData signature verification.
**Learning:** `hmac.compare_digest` should always be used over simple string comparisons (`!=` or `==`) for cryptographic hashes.
**Prevention:** Make sure developers understand how string comparisons can leak timing information on the server and mandate `hmac.compare_digest` in the codebase.

## 2025-02-28 - Prevented XSS in OAuth Callback
**Vulnerability:** XSS vulnerability in OAuth callback where `provider` and `email` were interpolated directly into the `HTMLResponse` template without sanitization.
**Learning:** External variables (such as those returned from OAuth providers) must be treated as untrusted input.
**Prevention:** Always sanitize variables using `html.escape()` before interpolating them into HTML strings.

## 2025-02-27 - [Fix Missing null coercion in hmac comparison]
**Vulnerability:** In Python, passing `None` to `hmac.compare_digest` raises a `TypeError`. Forms and requests with missing fields can evaluate to `None`, resulting in 500 errors.
**Learning:** Always coalesce potentially missing inputs (like `password or ""`) before passing them to `hmac.compare_digest` to ensure safe operation.
**Prevention:** Ensure that values passed to `hmac.compare_digest` are guaranteed to be strings or bytes, using a fallback value if they are not explicitly typed as required.

## 2025-02-27 - [XSS Vulnerability in Email Forwarding HTML Template]
**Vulnerability:** User-controlled inputs (`account.email`, `email.from_name`, `email.from_email`, `email.subject`, `otp`) were interpolated directly into the HTML formatted email body within `_build_forwarding_content` in `backend/app/services/forwarding_service.py` without proper sanitization. This could allow an attacker to craft an email with malicious HTML/JavaScript payloads in these fields, leading to Stored XSS when the forwarded email is viewed in a webmail client.
**Learning:** HTML strings must never have raw user input appended or formatted directly into them, even in secondary processes like email formatting or forwarding headers.
**Prevention:** Always use `html.escape(value or 'fallback')` on user-controlled inputs before interpolating them into HTML structures, ensuring optional/null values are safely cast to strings with defaults before escaping.
## 2024-05-31 - html.escape TypeError Vulnerability
**Vulnerability:** Passing `None` to `html.escape()` causes a `TypeError` which could lead to worker crashes or application failure when processing malicious or missing data.
**Learning:** `email_data.get("subject", "(No Subject)")` returns `None` if the `"subject"` key exists but its value is explicitly set to `None`. This means `html.escape(None)` will be called, crashing the worker process and potentially leading to denial of service if unhandled.
**Prevention:** Always use an inline boolean OR check (e.g. `html.escape(value or "default")`) or reassign the variable explicitly via `value = data.get("key") or "default"` to ensure a string is passed to `html.escape()`.
