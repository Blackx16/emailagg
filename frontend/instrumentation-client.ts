import posthog from "posthog-js";
import {
  scrubTelegramLaunchPayload,
} from "./src/lib/telegramUrl";

// Remove the Telegram Mini App launch payload from the URL before PostHog
// initializes and captures the first pageview/autocapture/session-recording
// metadata, so `tgWebAppData` (and the embedded user/auth_date/signature/hash)
// never reaches analytics.
// NOTE: This is now handled in AuthContext after the Telegram SDK has initialized
// to prevent race conditions where the URL is stripped before the SDK reads it.

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN!, {
  api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://teleforward-analytics.emaargroup.org",
  ui_host: "https://us.posthog.com",
  defaults: "2026-01-30",
  capture_exceptions: true,
  autocapture: true, // Explicitly enable autocapture for bounce rate
  capture_pageleave: true, // Explicitly enable pageleave capture for bounce rate
  debug: process.env.NODE_ENV === "development",
  // Defense-in-depth: redact the launch payload from URL properties on every
  // event in case it is ever reintroduced into window.location.
  before_send: scrubTelegramLaunchPayload,
});
