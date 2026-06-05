export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://lvh.me:8000";

interface FetchOptions extends RequestInit {
  token?: string | null;
}

export async function apiFetch(endpoint: string, options: FetchOptions = {}) {
  const { token, headers, ...rest } = options;
  
  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
  };
  
  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${BACKEND_URL}${endpoint}`, {
    headers: {
      ...defaultHeaders,
      ...headers,
    },
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
