"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = "emailagg_theme";

function getInitialTheme(): Theme {
  // 1. Check localStorage for explicit user override
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "light" || stored === "dark") return stored;
    } catch {
      // Storage may be blocked
    }

    // 2. Check Telegram WebApp colorScheme
    const win = window as any;
    if (win.Telegram?.WebApp?.colorScheme) {
      const tgScheme = win.Telegram.WebApp.colorScheme;
      if (tgScheme === "light" || tgScheme === "dark") return tgScheme;
    }

    // 3. Check OS preference via media query (browser dev/testing)
    if (window.matchMedia?.("(prefers-color-scheme: light)").matches) {
      return "light";
    }
  }

  // 4. Default to dark
  return "dark";
}

function applyTheme(theme: Theme) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark"); // SSR-safe default
  const [hasUserOverride, setHasUserOverride] = useState(false);

  // Initialize on mount
  useEffect(() => {
    const initial = getInitialTheme();
    setTheme(initial);
    applyTheme(initial);

    // Check if user has an explicit override
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "light" || stored === "dark") {
        setHasUserOverride(true);
      }
    } catch {
      // Ignore
    }
  }, []);

  // Listen for Telegram theme changes (auto-follow unless user has overridden)
  useEffect(() => {
    const win = window as any;
    if (!win.Telegram?.WebApp?.onEvent) return;

    const handleThemeChange = () => {
      // Only auto-follow if user hasn't manually set a preference
      if (hasUserOverride) return;
      
      const newScheme = win.Telegram.WebApp.colorScheme;
      if (newScheme === "light" || newScheme === "dark") {
        setTheme(newScheme);
        applyTheme(newScheme);
      }
    };

    win.Telegram.WebApp.onEvent("themeChanged", handleThemeChange);
    return () => {
      try {
        win.Telegram.WebApp.offEvent("themeChanged", handleThemeChange);
      } catch {
        // Ignore cleanup errors
      }
    };
  }, [hasUserOverride]);

  const toggleTheme = useCallback(() => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    setHasUserOverride(true);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage may be blocked
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
