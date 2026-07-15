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

## 2024-05-27 - Fix XSS Vulnerability in Forwarded HTML Emails
**Vulnerability:** User inputs (sender name, email address, subject) were interpolated directly into the HTML headers of forwarded emails, allowing for potential Cross-Site Scripting (XSS) in the recipient's mail client.
**Learning:** Even though we are forwarding emails to the user's *own* chosen inbox, an attacker could craft an email with a malicious subject or sender name. If those unsanitized strings are inserted into an HTML email payload, it creates an XSS vector when the user views the forwarded email in a webmail client.
**Prevention:** Always use `html.escape` (handling `None` gracefully) on any dynamic string before injecting it into an HTML template or email payload.
