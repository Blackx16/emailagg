import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, BACKEND_URL } from './api';

describe('apiFetch', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('should make a basic GET request with default headers', async () => {
    const mockResponse = { data: 'test' };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await apiFetch('/test-endpoint');

    expect(global.fetch).toHaveBeenCalledWith(`${BACKEND_URL}/test-endpoint`, {
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
      body: undefined,
    });
    expect(result).toEqual(mockResponse);
  });

  it('should include Authorization header if token is provided', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await apiFetch('/test', { token: 'my-secret-token' });

    expect(global.fetch).toHaveBeenCalledWith(`${BACKEND_URL}/test`, expect.objectContaining({
      headers: expect.objectContaining({
        'Authorization': 'Bearer my-secret-token',
      })
    }));
  });

  it('should merge additional headers', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await apiFetch('/test', { headers: { 'X-Custom-Header': 'custom' } });

    expect(global.fetch).toHaveBeenCalledWith(`${BACKEND_URL}/test`, expect.objectContaining({
      headers: expect.objectContaining({
        'X-Custom-Header': 'custom',
        'Content-Type': 'application/json',
      })
    }));
  });

  it('should JSON.stringify a plain object body', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const bodyObj = { foo: 'bar' };
    await apiFetch('/test', { method: 'POST', body: bodyObj });

    expect(global.fetch).toHaveBeenCalledWith(`${BACKEND_URL}/test`, expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(bodyObj),
    }));
  });

  it('should not JSON.stringify FormData', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const formData = new FormData();
    formData.append('key', 'value');
    await apiFetch('/test', { method: 'POST', body: formData });

    expect(global.fetch).toHaveBeenCalledWith(`${BACKEND_URL}/test`, expect.objectContaining({
      method: 'POST',
      body: formData,
    }));
  });

  it('should throw an error with detail message if response is not ok and contains detail', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Invalid credentials' }),
    });

    await expect(apiFetch('/test')).rejects.toThrow('Invalid credentials');
  });

  it('should throw a default error message if response is not ok and does not contain detail', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Some other error' }),
    });

    await expect(apiFetch('/test')).rejects.toThrow('API Request failed.');
  });

  it('should throw a default error message if response is not ok and json parsing fails', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      json: async () => { throw new Error('Cannot parse JSON'); },
    });

    await expect(apiFetch('/test')).rejects.toThrow('API Request failed.');
  });
});
