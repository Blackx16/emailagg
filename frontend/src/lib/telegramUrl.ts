// Telegram Mini App launch-payload scrubbing for analytics.
//
// When Telegram opens this dashboard as a WebApp it appends the launch payload
// to the URL fragment, e.g.
//   https://app.example.com/#tgWebAppData=...&tgWebAppVersion=7&tgWebAppPlatform=...
// The `tgWebAppData` blob is a URL-encoded query string that carries the
// signed-in `user` profile plus `auth_date`, `signature`, and `hash` — request
// authentication material. PostHog autocapture, pageviews, and session
// recordings all read `window.location.href`, so without scrubbing this
// sensitive payload is ingested into `$current_url` and recording start URLs.
//
// The app itself reads Telegram launch data from the `window.Telegram.WebApp`
// JS bridge (populated by telegram-web-app.js, loaded `beforeInteractive`), not
// from the URL, so it is safe to strip these params from the address bar once
// the page has loaded.
//
// Stripping can only happen after the SDK has read the URL (in AuthContext),
// so session recording — which captures its start URL at init — is deferred
// until then whenever launch params are present (see hasTelegramLaunchParams).

// Any param whose (lower-cased) name starts with this prefix is a Telegram
// launch parameter (tgWebAppData, tgWebAppVersion, tgWebAppThemeParams, ...).
const TELEGRAM_PARAM_PREFIX = "tgwebapp";

// Sensitive field names that can appear either as top-level params or as the
// decoded contents of tgWebAppData.
const SENSITIVE_PARAM_KEYS = new Set([
  "user",
  "auth_date",
  "signature",
  "hash",
  "query_id",
  "chat_instance",
  "chat_type",
]);

function isSensitiveKey(key: string): boolean {
  const k = key.toLowerCase();
  return k.startsWith(TELEGRAM_PARAM_PREFIX) || SENSITIVE_PARAM_KEYS.has(k);
}

// Does a `?query` / `#fragment` style segment contain any sensitive key?
function segmentHasSensitiveKey(segment: string): boolean {
  if (!segment) return false;
  const params = new URLSearchParams(segment);
  for (const key of Array.from(params.keys())) {
    if (isSensitiveKey(key)) return true;
  }
  return false;
}

// Strip sensitive keys from a `?query` / `#fragment` style segment (without the
// leading `?` or `#`). Returns the cleaned segment, or the original string
// untouched when there was nothing to remove so that plain anchors such as
// `rules` and unrelated params such as `tab=inbox` are preserved verbatim.
function sanitizeSegment(segment: string): string {
  if (!segment) return "";
  const params = new URLSearchParams(segment);
  let changed = false;
  for (const key of Array.from(params.keys())) {
    if (isSensitiveKey(key)) {
      params.delete(key);
      changed = true;
    }
  }
  if (!changed) return segment;
  return params.toString();
}

// Return `rawUrl` with the Telegram launch payload removed from both the query
// string and the fragment. Non-Telegram params/anchors are preserved. Falls
// back to returning the input unchanged if it cannot be parsed as a URL.
export function sanitizeTelegramUrl(rawUrl: string): string {
  if (!rawUrl) return rawUrl;
  try {
    const url = new URL(rawUrl);
    const cleanedSearch = sanitizeSegment(url.search.replace(/^\?/, ""));
    const cleanedHash = sanitizeSegment(url.hash.replace(/^#/, ""));
    url.search = cleanedSearch ? `?${cleanedSearch}` : "";
    url.hash = cleanedHash ? `#${cleanedHash}` : "";
    return url.toString();
  } catch {
    return rawUrl;
  }
}

// Does `rawUrl` (default: the current browser URL) carry a Telegram launch
// payload? Used at PostHog init to decide whether session recording must be
// deferred until the URL has been scrubbed — see stripTelegramLaunchParamsFromLocation.
export function hasTelegramLaunchParams(rawUrl?: string): boolean {
  const url =
    rawUrl ?? (typeof window !== "undefined" ? window.location.href : "");
  if (!url) return false;
  try {
    const u = new URL(url);
    return (
      segmentHasSensitiveKey(u.search.replace(/^\?/, "")) ||
      segmentHasSensitiveKey(u.hash.replace(/^#/, ""))
    );
  } catch {
    return false;
  }
}

// Remove the Telegram launch payload from the current browser URL via
// history.replaceState so that neither autocapture/pageviews nor session
// recordings (which read window.location.href) ever see it. Safe to call more
// than once; never throws.
export function stripTelegramLaunchParamsFromLocation(): void {
  if (typeof window === "undefined") return;
  try {
    const current = window.location.href;
    const cleaned = sanitizeTelegramUrl(current);
    if (cleaned !== current) {
      window.history.replaceState(window.history.state, "", cleaned);
    }
  } catch {
    // Never let URL cleanup interfere with app startup.
  }
}

// URL-bearing PostHog properties that can carry the launch payload.
const URL_PROPERTY_KEYS = [
  "$current_url",
  "$referrer",
  "$initial_current_url",
  "$initial_referrer",
];

// PostHog `before_send` hook: redact the Telegram launch payload from URL
// properties on every outgoing event (including `$snapshot` session-recording
// events) as defense-in-depth alongside stripTelegramLaunchParamsFromLocation.
export function scrubTelegramLaunchPayload<T extends { properties?: Record<string, unknown> } | null>(
  event: T,
): T {
  if (!event || !event.properties) return event;
  const props = event.properties;
  for (const key of URL_PROPERTY_KEYS) {
    const value = props[key];
    if (typeof value === "string" && value) {
      props[key] = sanitizeTelegramUrl(value);
    }
  }
  return event;
}
