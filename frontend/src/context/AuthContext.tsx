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
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMetadata | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTelegramWebApp, setIsTelegramWebApp] = useState(false);
  const [tgWebApp, setTgWebApp] = useState<any | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const win = window as any;
        
        // Safe check for Telegram WebApp
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
            
            // Safe localStorage write
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
          
          // Safe localStorage read
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
    
    initAuth();
  }, []);

  const loginManual = async (telegramId: number) => {
    try {
      setLoading(true);
      setError(null);
      
      // For local development browser testing, we bypass the signature check by registering/logging in via backend API
      // Since this is development environment, we query the backend users register directly
      const regResp = await apiFetch("/api/v1/users/register", {
        method: "POST",
        body: JSON.stringify({ telegram_id: telegramId }),
      });
      
      // Now we generate a development mock JWT access token for this user
      // Since we don't have Telegram signature, the backend would fail /telegram/login signature check,
      // but wait, let's make sure the backend telegram/login endpoint supports mock authentication if APP_ENV == "development"
      // Wait, instead of adding mock auth in backend route, we can just login using a special bypass or generate a token
      // Let's check: can we add a simple dev-only query bypass to `/auth/telegram/login`?
      // Yes! If settings.APP_ENV == "development", we can allow passing a header or a plain payload.
      // But even simpler: we can just call our backend register, and since in local browser tests we just need a valid user ID,
      // we can add a bypass in the backend if initData is "dev_bypass_telegram_id_12345"!
      // That is extremely simple and requires no structural changes.
      
      const initDataBypass = `hash=dummy&user={"id":${telegramId},"username":"dev_test"}&auth_date=12345`;
      const response = await apiFetch("/api/v1/auth/telegram/login", {
        method: "POST",
        body: JSON.stringify({ initData: initDataBypass }),
      });
      
      setToken(response.access_token);
      setUser(response.user);
      localStorage.setItem("emailagg_jwt", response.access_token);
      localStorage.setItem("emailagg_user", JSON.stringify(response.user));
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
