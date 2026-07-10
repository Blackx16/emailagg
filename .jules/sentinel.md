## 2024-07-06 - Prevented Timing Attack in Telegram Auth Verification
**Vulnerability:** Timing attack possible during Telegram initData signature verification.
**Learning:** `hmac.compare_digest` should always be used over simple string comparisons (`!=` or `==`) for cryptographic hashes.
**Prevention:** Make sure developers understand how string comparisons can leak timing information on the server and mandate `hmac.compare_digest` in the codebase.

## 2025-02-28 - Prevented XSS in OAuth Callback
**Vulnerability:** XSS vulnerability in OAuth callback where `provider` and `email` were interpolated directly into the `HTMLResponse` template without sanitization.
**Learning:** External variables (such as those returned from OAuth providers) must be treated as untrusted input.
**Prevention:** Always sanitize variables using `html.escape()` before interpolating them into HTML strings.
