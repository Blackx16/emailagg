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
## 2025-05-18 - Missing Fallbacks for `html.escape()` Vulnerability
**Vulnerability:** Calls to `html.escape()` were found receiving variables without a fallback. This can lead to a `TypeError` if the variable is `None`, which crashes the application or causes unhandled exceptions leading to a 500 server error rather than failing gracefully.
**Learning:** `html.escape()` explicitly requires a string input. Many parsed values from external APIs or databases (like email from addresses, or optional subjects) might end up being `None`.
**Prevention:** Always ensure that `html.escape()` receives a valid string by using conditional fallbacks like `html.escape(variable if variable else "Fallback value")` or `html.escape(variable or "Fallback value")`.
