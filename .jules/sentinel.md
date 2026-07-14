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

## 2025-02-28 - Prevented XSS in Email Forwarding Templates
**Vulnerability:** XSS vulnerability in email forwarding service where the original sender's name, email, subject, and the extracted OTP were interpolated directly into the HTML forwarding template without sanitization.
**Learning:** External data from incoming emails (which can be easily spoofed or crafted maliciously) must be treated as untrusted input.
**Prevention:** Always sanitize variables using `html.escape()` before interpolating them into HTML strings, even for internal email templates like forwarding headers.
