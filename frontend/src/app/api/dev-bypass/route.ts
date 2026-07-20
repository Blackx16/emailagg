import { NextRequest, NextResponse } from "next/server";

// For server-side API routes, use the internal Docker network URL
const BACKEND_URL = process.env.INTERNAL_BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || "";
const DEV_BYPASS_SECRET = process.env.DEV_BYPASS_SECRET || "emaar";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { telegram_id, bypass_secret } = body;

    // Verify the client-side bypass secret
    if (bypass_secret !== DEV_BYPASS_SECRET) {
      return NextResponse.json(
        { detail: "Invalid bypass secret." },
        { status: 403 }
      );
    }

    if (!telegram_id || isNaN(Number(telegram_id))) {
      return NextResponse.json(
        { detail: "Invalid telegram_id." },
        { status: 400 }
      );
    }

    // Proxy to backend with the real INTERNAL_API_KEY (server-side only)
    const backendRes = await fetch(`${BACKEND_URL}/api/v1/auth/telegram/dev-bypass`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        telegram_id: Number(telegram_id),
        bypass_key: INTERNAL_API_KEY,
      }),
    });

    const data = await backendRes.json();

    if (!backendRes.ok) {
      return NextResponse.json(data, { status: backendRes.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Dev bypass proxy error:", error);
    return NextResponse.json(
      { detail: error.message || "Internal server error." },
      { status: 500 }
    );
  }
}
