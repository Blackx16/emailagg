'use client'

import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import {
  hasTelegramLaunchParams,
  scrubTelegramLaunchPayload,
} from '@/lib/telegramUrl'

if (typeof window !== 'undefined') {
  // The Telegram launch payload can only be stripped from the URL after the
  // Telegram SDK has read it (done in AuthContext). Session recording captures
  // its start URL at init, so when launch params are present we defer recording
  // until AuthContext has scrubbed the URL and calls posthog.startSessionRecording().
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY || 'phc_yMbzeXj5PXsGTpU7dAzcuf3vJbmhuRLqa8raFfwcCkZm', {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://teleforward-analytics.emaargroup.org',
    person_profiles: 'identified_only', // or 'always' to create profiles for anonymous users as well
    capture_pageview: false, // Disable automatic pageview capture, as we capture manually
    autocapture: true, // Explicitly enable autocapture for bounce rate
    capture_pageleave: true, // Explicitly enable pageleave capture for bounce rate
    disable_session_recording: hasTelegramLaunchParams(),
    // Defense-in-depth: redact the launch payload from URL properties on every event.
    before_send: scrubTelegramLaunchPayload,
  })
}

export function CSPostHogProvider({ children }: { children: React.ReactNode }) {
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}
