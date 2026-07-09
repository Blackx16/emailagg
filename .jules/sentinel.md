## 2024-05-18 - [Fix XSS in OAuth Callback]
**Vulnerability:** The OAuth callback endpoint (`backend/app/api/routes/auth.py`) returned an `HTMLResponse` that interpolated user-controlled variables (`provider` and `email`) directly into the HTML string without any escaping.
**Learning:** Even data originating from trusted OAuth providers should be treated as untrusted and sanitized before being rendered in HTML to prevent XSS. A malicious or hijacked provider could send crafted data.
**Prevention:** Always use `html.escape()` or an established templating engine (like Jinja2) that auto-escapes variables when generating HTML responses.
