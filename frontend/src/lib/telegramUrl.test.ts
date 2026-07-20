import { describe, it, expect } from 'vitest';
import {
  hasTelegramLaunchParams,
  sanitizeTelegramUrl,
  scrubTelegramLaunchPayload,
  stripTelegramLaunchParamsFromLocation,
} from './telegramUrl';

describe('sanitizeTelegramUrl', () => {
  it('strips the Telegram launch payload from the fragment', () => {
    const raw =
      'https://app.example.com/#tgWebAppData=query_id%3DAAE%26user%3D%257B%2522id%2522%253A1%257D%26auth_date%3D1700000000%26signature%3Dabc%26hash%3Ddef&tgWebAppVersion=7.0&tgWebAppPlatform=tdesktop';
    expect(sanitizeTelegramUrl(raw)).toBe('https://app.example.com/');
  });

  it('strips sensitive params from the query string', () => {
    const raw =
      'https://app.example.com/?tab=inbox&user=%7B%22id%22%3A1%7D&auth_date=1700000000&signature=abc&hash=def';
    expect(sanitizeTelegramUrl(raw)).toBe('https://app.example.com/?tab=inbox');
  });

  it('preserves a plain #rules anchor', () => {
    expect(sanitizeTelegramUrl('https://app.example.com/#rules')).toBe(
      'https://app.example.com/#rules',
    );
  });

  it('preserves unrelated query params untouched', () => {
    const raw = 'https://app.example.com/?tab=mailboxes';
    expect(sanitizeTelegramUrl(raw)).toBe(raw);
  });

  it('keeps non-Telegram fragment params when removing a Telegram one', () => {
    const raw = 'https://app.example.com/#foo=bar&tgWebAppData=secret';
    expect(sanitizeTelegramUrl(raw)).toBe('https://app.example.com/#foo=bar');
  });

  it('returns unparseable input unchanged', () => {
    expect(sanitizeTelegramUrl('not a url')).toBe('not a url');
    expect(sanitizeTelegramUrl('')).toBe('');
  });
});

describe('hasTelegramLaunchParams', () => {
  it('detects tgWebAppData in the fragment', () => {
    expect(
      hasTelegramLaunchParams(
        'https://app.example.com/#tgWebAppData=query_id%3DAAE%26hash%3Ddef&tgWebAppVersion=7.0',
      ),
    ).toBe(true);
  });

  it('detects sensitive params in the query string', () => {
    expect(
      hasTelegramLaunchParams(
        'https://app.example.com/?tab=inbox&signature=abc',
      ),
    ).toBe(true);
  });

  it('returns false for a clean URL', () => {
    expect(hasTelegramLaunchParams('https://app.example.com/?tab=inbox')).toBe(
      false,
    );
    expect(hasTelegramLaunchParams('https://app.example.com/#rules')).toBe(
      false,
    );
  });

  it('returns false for unparseable or empty input', () => {
    expect(hasTelegramLaunchParams('not a url')).toBe(false);
    expect(hasTelegramLaunchParams('')).toBe(false);
  });
});

describe('scrubTelegramLaunchPayload', () => {
  it('redacts URL-bearing properties on an event', () => {
    const event = {
      event: '$autocapture',
      properties: {
        $current_url: 'https://app.example.com/#tgWebAppData=secret&tgWebAppVersion=7.0',
        $referrer: 'https://app.example.com/?signature=abc&tab=inbox',
        $other: 'untouched',
      },
    };
    const result = scrubTelegramLaunchPayload(event)!;
    expect(result.properties.$current_url).toBe('https://app.example.com/');
    expect(result.properties.$referrer).toBe('https://app.example.com/?tab=inbox');
    expect(result.properties.$other).toBe('untouched');
  });

  it('passes null through (dropped events)', () => {
    expect(scrubTelegramLaunchPayload(null)).toBeNull();
  });

  it('handles events without properties', () => {
    const event = { event: '$pageview' } as { event: string; properties?: Record<string, unknown> };
    expect(scrubTelegramLaunchPayload(event)).toBe(event);
  });
});

describe('stripTelegramLaunchParamsFromLocation', () => {
  it('is a no-op without a window (SSR/node)', () => {
    expect(() => stripTelegramLaunchParamsFromLocation()).not.toThrow();
  });
});
