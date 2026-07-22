import posthog from "posthog-js";
import {
  hasTelegramLaunchParams,
  scrubTelegramLaunchPayload,
} from "./src/lib/telegramUrl";

// The Telegram Mini App launch payload (`tgWebAppData` and the embedded
// user/auth_date/signature/hash) arrives in the URL. It can only be stripped
// once the Telegram SDK has read it, which happens in AuthContext — stripping
// it earlier races the SDK and breaks authentication.
//
// Session recording captures its start URL from window.location.href the moment
// it begins, i.e. before AuthContext can scrub it — that is how the payload
// leaked into recording metadata. So when launch params are present we defer
// recording until AuthContext has scrubbed the URL (it then calls
// posthog.startSessionRecording()). A regular browser has nothing sensitive in
// the URL, so recording starts immediately.
const deferSessionRecording = hasTelegramLaunchParams();

posthog.init(process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN!, {
  api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://teleforward-analytics.emaargroup.org",
  ui_host: "https://us.posthog.com",
  defaults: "2026-01-30",
  capture_exceptions: true,
  autocapture: true, // Explicitly enable autocapture for bounce rate
  capture_pageleave: true, // Explicitly enable pageleave capture for bounce rate
  disable_session_recording: deferSessionRecording,
  debug: process.env.NODE_ENV === "development",
  // Defense-in-depth: redact the launch payload from URL properties on every
  // event in case it is ever reintroduced into window.location.
  before_send: scrubTelegramLaunchPayload,
});
