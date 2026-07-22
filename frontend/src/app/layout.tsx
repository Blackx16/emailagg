import type { Metadata } from "next";
import Script from "next/script";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { CSPostHogProvider } from "./providers";
import SuspendedPostHogPageView from "./PostHogPageView";
import "./globals.css";

export const metadata: Metadata = {
  title: "EmailAgg Dashboard",
  description: "Your unified email command center inside Telegram",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="font-sans h-full antialiased"
      suppressHydrationWarning
    >
      <head>
        {/* Load Telegram WebApp JS library to interface with Telegram Client */}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className="min-h-full flex flex-col text-[var(--text-primary)]" style={{ backgroundColor: 'var(--bg)' }}>
        <CSPostHogProvider>
          <SuspendedPostHogPageView />
          <ThemeProvider>
            <AuthProvider>{children}</AuthProvider>
          </ThemeProvider>
        </CSPostHogProvider>
      </body>
    </html>
  );
}
