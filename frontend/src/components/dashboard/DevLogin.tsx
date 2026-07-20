"use client";

import React, { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Mail, AlertCircle, ShieldCheck, Sparkles, Loader2, ArrowRight } from "lucide-react";

interface DevLoginProps {
  error: string | null;
  loginManual: (id: number) => Promise<void>;
}

function DevLoginContent({ error, loginManual }: DevLoginProps) {
  const [devTelegramId, setDevTelegramId] = useState("");
  const [devLoginLoading, setDevLoginLoading] = useState(false);
  const [devLoginError, setDevLoginError] = useState<string | null>(null);
  const [showBypass, setShowBypass] = useState(false);
  const searchParams = useSearchParams();

  React.useEffect(() => {
    // Check both searchParams and window location as fallbacks
    const hasBypassParam = searchParams?.has("bypass") && searchParams?.get("bypass") === "emaar";
    const hasBypassUrl = typeof window !== "undefined" && window.location.search.includes("bypass=emaar");
    
    if (hasBypassParam || hasBypassUrl) {
      setShowBypass(true);
    }
  }, [searchParams]);

  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!devTelegramId) return;
    
    setDevLoginLoading(true);
    setDevLoginError(null);
    
    try {
      const parsedId = parseInt(devTelegramId);
      if (isNaN(parsedId)) {
        throw new Error("Telegram ID must be a valid number.");
      }
      await loginManual(parsedId);
    } catch (err: any) {
      setDevLoginError(err.message || "Failed to log in.");
    } finally {
      setDevLoginLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#090a0f]">
      {/* Glow backdrop decorative bubbles */}
      <div className="absolute top-1/4 left-1/4 h-80 w-80 rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 h-80 w-80 rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none" />

      <div className="max-w-md w-full glass-card rounded-xl p-8 shadow-sm relative border border-slate-700">
        <div className="flex justify-center mb-5">
          <div className="h-14 w-14 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg">
            <Mail className="h-7 w-7 text-white" />
          </div>
        </div>
        
        <h1 className="text-3xl font-bold text-center text-slate-100 tracking-tight mb-1">
          EmailAgg
        </h1>
        <p className="text-xs text-center text-slate-400 mb-6">
          Unified Inbox Intelligence & Telegram Alert SaaS
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Setup guidance warning */}
        <div className="mb-6 p-4 rounded-xl bg-slate-800 border border-slate-700 space-y-2 text-xs leading-relaxed text-slate-300">
          <div className="flex items-center space-x-1.5 font-semibold text-cyan-400">
            <ShieldCheck className="h-4 w-4" />
            <span>Telegram Web App Access</span>
          </div>
          <p>
            This dashboard is designed to run natively inside your Telegram Bot client. Message the bot and tap the menu to open this app.
          </p>
        </div>

        {showBypass && (
          <form onSubmit={handleDevLogin} className="space-y-4 border-t border-slate-700/80 pt-5">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center">
              <Sparkles className="h-3.5 w-3.5 text-indigo-400 mr-1" />
              Developer Bypass Authentication
            </h3>
            <div>
              <label htmlFor="telegramId" className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                Enter Test Telegram ID
              </label>
              <input
                id="telegramId"
                type="text"
                value={devTelegramId}
                onChange={(e) => setDevTelegramId(e.target.value)}
                placeholder="e.g. 5053093069"
                required
                className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
              />
            </div>

            {devLoginError && (
              <p className="text-xs text-rose-400">{devLoginError}</p>
            )}

            <button
              type="submit"
              disabled={devLoginLoading}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition duration-200 cursor-pointer shadow-md shadow-indigo-950/50"
            >
              {devLoginLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Bypass to Dashboard</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function DevLogin(props: DevLoginProps) {
  return (
    <Suspense fallback={<div className="flex-1 bg-[#090a0f]" />}>
      <DevLoginContent {...props} />
    </Suspense>
  );
}
