## 2024-07-06 - Prevented Timing Attack in Telegram Auth Verification
**Vulnerability:** Timing attack possible during Telegram initData signature verification.
**Learning:** `hmac.compare_digest` should always be used over simple string comparisons (`!=` or `==`) for cryptographic hashes.
**Prevention:** Make sure developers understand how string comparisons can leak timing information on the server and mandate `hmac.compare_digest` in the codebase.
