export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://lvh.me:8000";

// Override `body` to also accept plain objects — apiFetch will JSON.stringify them.
interface FetchOptions extends Omit<RequestInit, "body"> {
  token?: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body?: Record<string, any> | BodyInit | null;
}

export async function apiFetch(endpoint: string, options: FetchOptions = {}) {
  const { token, headers, body, ...rest } = options;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
  };

  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  // Auto-serialize plain objects so callers don't have to JSON.stringify themselves.
  const serializedBody: BodyInit | null | undefined =
    body !== null && body !== undefined && typeof body === "object" &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    !(body instanceof ReadableStream) &&
    !(body instanceof Blob) &&
    !(body instanceof ArrayBuffer)
      ? JSON.stringify(body)
      : (body as BodyInit | null | undefined);

  const response = await fetch(`${BACKEND_URL}${endpoint}`, {
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    body: serializedBody,
    ...rest,
  });

  if (!response.ok) {
    let errorDetail = "API Request failed.";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
