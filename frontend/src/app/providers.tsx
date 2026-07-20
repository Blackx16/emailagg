'use client'

import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import {
  scrubTelegramLaunchPayload,
} from '@/lib/telegramUrl'

if (typeof window !== 'undefined') {
  // Strip the Telegram launch payload from the URL before init so it never
  // reaches pageviews, autocapture, or session recording metadata.
  // Note: We now do this in AuthContext after the Telegram SDK has initialized
  // to prevent race conditions where the URL is stripped before the SDK reads it.
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY || 'phc_yMbzeXj5PXsGTpU7dAzcuf3vJbmhuRLqa8raFfwcCkZm', {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://teleforward-analytics.emaargroup.org',
    person_profiles: 'identified_only', // or 'always' to create profiles for anonymous users as well
    capture_pageview: false, // Disable automatic pageview capture, as we capture manually
    autocapture: true, // Explicitly enable autocapture for bounce rate
    capture_pageleave: true, // Explicitly enable pageleave capture for bounce rate
    // Defense-in-depth: redact the launch payload from URL properties on every event.
    before_send: scrubTelegramLaunchPayload,
  })
}

export function CSPostHogProvider({ children }: { children: React.ReactNode }) {
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}
