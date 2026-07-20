"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface UserMetadata {
  id: string;
  telegram_id: number;
  email: string | null;
  plan: string;
}

interface AuthContextType {
  user: UserMetadata | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  isTelegramWebApp: boolean;
  tgWebApp: any | null;
  loginManual: (telegramId: number) => Promise<void>;
  logout: () => void;
  retryLogin: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMetadata | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTelegramWebApp, setIsTelegramWebApp] = useState(false);
  const [tgWebApp, setTgWebApp] = useState<any | null>(null);

  const initAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const win = window as any;
      
      // Wait briefly for Telegram SDK to inject initData if it's not ready instantly
      if (win.Telegram && win.Telegram.WebApp && !win.Telegram.WebApp.initData) {
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      const isTg = !!(
        win.Telegram &&
        win.Telegram.WebApp &&
        win.Telegram.WebApp.initData
      );
      
      if (isTg) {
        const wa = win.Telegram.WebApp;
        setTgWebApp(wa);
        setIsTelegramWebApp(true);
        
        try {
          wa.ready();
          wa.expand();
        } catch (e) {
          console.warn("Failed to call Telegram WebApp SDK ready/expand:", e);
        }
        
        try {
          setError(null);
          const response = await apiFetch("/api/v1/auth/telegram/login", {
            method: "POST",
            body: JSON.stringify({ initData: wa.initData }),
          });
          
          setToken(response.access_token);
          setUser(response.user);
          
          try {
            localStorage.setItem("emailagg_jwt", response.access_token);
            localStorage.setItem("emailagg_user", JSON.stringify(response.user));
          } catch (e) {
            console.warn("Storage write failed:", e);
          }
        } catch (err: any) {
          console.error("Telegram WebApp authentication failed:", err);
          setError(err.message || "Failed to authenticate with Telegram.");
        }
      } else {
        setIsTelegramWebApp(false);
        
        try {
          const savedToken = localStorage.getItem("emailagg_jwt");
          const savedUser = localStorage.getItem("emailagg_user");
          
          if (savedToken && savedUser) {
            setToken(savedToken);
            try {
              setUser(JSON.parse(savedUser));
            } catch (e) {
              console.error("Failed to parse saved user JSON:", e);
              localStorage.removeItem("emailagg_jwt");
              localStorage.removeItem("emailagg_user");
            }
          }
        } catch (e) {
          console.warn("Storage access failed or is blocked by browser security:", e);
        }
      }
    } catch (globalError: any) {
      console.error("Global auth initialization error:", globalError);
      setError(globalError.message || "Initialization failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initAuth();
  }, []);

  const loginManual = async (telegramId: number) => {
    try {
      setLoading(true);
      setError(null);
      
      // Call the Next.js server-side API route which proxies to backend
      const response = await fetch("/api/dev-bypass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          telegram_id: telegramId,
          bypass_secret: "emaar",
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Dev bypass failed (HTTP ${response.status}).`);
      }
      
      const data = await response.json();
      
      setToken(data.access_token);
      setUser(data.user);
      
      try {
        localStorage.setItem("emailagg_jwt", data.access_token);
        localStorage.setItem("emailagg_user", JSON.stringify(data.user));
      } catch (e) {
        console.warn("Storage write failed:", e);
      }
    } catch (err: any) {
      console.error("Manual dev login failed:", err);
      setError(err.message || "Bypass authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("emailagg_jwt");
    localStorage.removeItem("emailagg_user");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        error,
        isTelegramWebApp,
        tgWebApp,
        loginManual,
        logout,
        retryLogin: initAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
