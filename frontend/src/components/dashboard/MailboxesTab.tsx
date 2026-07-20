import React, { useState } from "react";
import { Activity, BellRing, SlidersHorizontal, Loader2, Trash2, AlertCircle, Plus, Mail, Sparkles } from "lucide-react";
import { Account } from "../../types/dashboard";

interface MailboxesTabProps {
  user: any;
  token: string | null;
  accounts: Account[];
  notifLimitEffective: number;
  notifLimitFloor: number;
  notifLimitInput: string;
  setNotifLimitInput: (val: string) => void;
  notifLimitSaving: boolean;
  saveNotifLimit: () => void;
  handleMassTogglePreference: (field: string, value: boolean) => void;
  handleTogglePreference: (accountId: string, field: string, value: boolean) => void;
  handleDisconnect: (accountId: string) => void;
  handleOAuthConnect: (provider: "google" | "microsoft") => void;
  fetchData: () => void;
}

export default function MailboxesTab({
  user, token, accounts,
  notifLimitEffective, notifLimitFloor, notifLimitInput, setNotifLimitInput, notifLimitSaving, saveNotifLimit,
  handleMassTogglePreference, handleTogglePreference, handleDisconnect, handleOAuthConnect, fetchData
}: MailboxesTabProps) {
  const [showImapDialog, setShowImapDialog] = useState(false);
  const [imapHost, setImapHost] = useState("");
  const [imapPort, setImapPort] = useState("993");
  const [imapEmail, setImapEmail] = useState("");
  const [imapPassword, setImapPassword] = useState("");
  const [imapConnecting, setImapConnecting] = useState(false);
  const [imapError, setImapError] = useState<string | null>(null);

  const handleImapConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    setImapConnecting(true);
    setImapError(null);
    try {
      const res = await fetch("/api/mail/accounts/imap", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          email: imapEmail,
          password: imapPassword,
          imap_host: imapHost,
          imap_port: parseInt(imapPort) || 993,
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to connect IMAP account");
      }

      setShowImapDialog(false);
      setImapEmail("");
      setImapPassword("");
      setImapHost("");
      fetchData();
    } catch (err: any) {
      setImapError(err.message || "An unexpected error occurred");
    } finally {
      setImapConnecting(false);
    }
  };

  const activeAccounts = accounts.filter(a => a.status !== "disconnected");
  const allDashEnabled = activeAccounts.length > 0 && activeAccounts.every(a => a.deliver_to_dashboard);
  const allAlertsEnabled = activeAccounts.length > 0 && activeAccounts.every(a => a.notify_telegram);
  const allForwardEnabled = activeAccounts.length > 0 && activeAccounts.every(a => a.forward_enabled);

  return (
    <div className="space-y-6">
      
      {/* Global Settings & Controls Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 mb-2 rounded-xl glass border border-slate-700 divide-y lg:divide-y-0 lg:divide-x divide-slate-800/50 shadow-md">
        
        {/* Accounts limits */}
        <div className="flex flex-col justify-between text-left p-5">
          <div className="space-y-1 mb-4">
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-slate-400" />
              Limit Tracking
            </h3>
            <p className="text-[10px] text-slate-400">
              Plan boundaries governed by subscription.
            </p>
          </div>
          <div className="flex items-end justify-between mt-auto">
            <span className="text-2xl font-black text-white leading-none tracking-tight">
              {activeAccounts.length}
            </span>
            <span className="text-xs text-slate-500 font-bold mb-0.5">
              / {user?.plan === "free" ? 3 : user?.plan === "pro" ? 25 : 100} limit
            </span>
          </div>
        </div>

        {/* Notification Throttle */}
        <div className="flex flex-col text-left p-5 space-y-3 justify-between">
          <div>
            <div className="flex items-start justify-between mb-1">
              <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                <BellRing className="h-3.5 w-3.5 text-slate-400" />
                Throttle
              </h3>
              <span className="text-[9px] text-slate-500 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded shrink-0 ml-2">
                <b className="text-indigo-400">{notifLimitEffective}</b>/hr effective
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Max Telegram alerts. Floor is <span className="text-indigo-400 font-bold">{notifLimitFloor}/hr</span>.
            </p>
          </div>
          <div className="flex items-center space-x-2 mt-auto pt-2">
            <input
              type="number"
              min={1}
              value={notifLimitInput}
              onChange={(e) => setNotifLimitInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveNotifLimit()}
              className="w-16 px-2 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-center shadow-inner"
            />
            <button
              onClick={saveNotifLimit}
              disabled={notifLimitSaving}
              className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition cursor-pointer disabled:opacity-50"
            >
              {notifLimitSaving ? "..." : "Save"}
            </button>
            {parseInt(notifLimitInput) < notifLimitFloor && (
              <span className="text-[9px] text-amber-400/80 ml-auto flex items-center"><AlertCircle className="w-3 h-3 mr-0.5"/> Floor</span>
            )}
          </div>
        </div>

        {/* Mass Controls */}
        <div className={`flex flex-col text-left p-5 justify-between ${activeAccounts.length === 0 ? "opacity-40" : ""}`}>
          <div>
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5 mb-1">
              <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
              Mass Controls
            </h3>
            <p className="text-[10px] text-slate-400 leading-relaxed">
              {activeAccounts.length === 0 ? "No active mailboxes." : "Apply preferences to all active mailboxes."}
            </p>
          </div>
          
          {activeAccounts.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[9px] font-semibold text-slate-400 mt-3 pt-3 border-t border-slate-700/50">
              <label className="flex items-center space-x-1.5 cursor-pointer select-none group" title="Dash Delivery for all">
                <input
                  type="checkbox"
                  checked={allDashEnabled}
                  onChange={(e) => handleMassTogglePreference("deliver_to_dashboard", e.target.checked)}
                  className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                />
                <span className="group-hover:text-slate-300 transition-colors">📬 Dash</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none group" title="Telegram Alerts for all">
                <input
                  type="checkbox"
                  checked={allAlertsEnabled}
                  onChange={(e) => handleMassTogglePreference("notify_telegram", e.target.checked)}
                  className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                />
                <span className="group-hover:text-slate-300 transition-colors">🔔 Alerts</span>
              </label>

              <label className="flex items-center space-x-1.5 cursor-pointer select-none group" title="Email Forwarding for all">
                <input
                  type="checkbox"
                  checked={allForwardEnabled}
                  onChange={(e) => handleMassTogglePreference("forward_enabled", e.target.checked)}
                  className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                />
                <span className="group-hover:text-slate-300 transition-colors">📤 Fwd</span>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* List of Connected Mailboxes */}
      <div>
        <h3 className="text-[10px] uppercase tracking-widest font-bold text-slate-400 mb-3 px-1 text-left">
          Your Connected Mailboxes
        </h3>

        {activeAccounts.length === 0 ? (
          <div className="p-8 text-center glass-card rounded-xl border border-slate-700 text-slate-400 text-xs mb-6">
            No active mailboxes connected. Add an account below to begin.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {activeAccounts.map((acc) => (
              <div key={acc.id} className="p-4 rounded-xl glass-card text-left border border-slate-700 flex flex-col justify-between min-h-[175px]">
                <div className="flex items-start justify-between">
                  <div>
                    <span className={`text-[8px] uppercase tracking-widest font-black px-1.5 py-0.5 rounded ${
                      acc.provider === "microsoft" ? "bg-blue-950/60 border border-blue-900/40 text-blue-400" :
                      acc.provider === "google" ? "bg-red-950/60 border border-red-900/40 text-red-400" :
                      "bg-slate-900 border border-slate-700 text-slate-400"
                    }`}>
                      {acc.provider}
                    </span>
                    <h4 className="text-xs font-bold text-white mt-2.5 truncate max-w-[200px]" title={acc.email}>
                      {acc.email}
                    </h4>
                  </div>

                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center ${
                    acc.status === "active" ? "bg-emerald-900/20 border border-emerald-900/30 text-emerald-400" :
                    acc.status === "syncing" ? "bg-indigo-900/20 border border-indigo-900/30 text-indigo-400" :
                    acc.status === "error" ? "bg-rose-900/20 border border-rose-900/30 text-rose-400 animate-pulse" :
                    "bg-slate-900 border border-slate-700 text-slate-400"
                  }`}>
                    {acc.status === "syncing" && <Loader2 className="h-3 w-3 animate-spin mr-1 text-indigo-400 shrink-0" />}
                    {acc.status === "active" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1.5 shrink-0" />}
                    {acc.status === "error" && <AlertCircle className="h-3 w-3 mr-1 text-rose-400 shrink-0" />}
                    {acc.status.toUpperCase()}
                  </span>
                </div>

                {/* Preferences Toggles */}
                <div className="mt-3.5 pt-2 border-t border-slate-700/50 grid grid-cols-3 gap-1.5 text-[9px] font-semibold text-slate-400">
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Show incoming emails on dashboard">
                    <input
                      type="checkbox"
                      checked={acc.deliver_to_dashboard}
                      onChange={(e) => handleTogglePreference(acc.id, "deliver_to_dashboard", e.target.checked)}
                      className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                    />
                    <span>📬 Dash</span>
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Send alerts to your Telegram bot">
                    <input
                      type="checkbox"
                      checked={acc.notify_telegram}
                      onChange={(e) => handleTogglePreference(acc.id, "notify_telegram", e.target.checked)}
                      className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                    />
                    <span>🔔 Alerts</span>
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Enable custom email forwarding rules">
                    <input
                      type="checkbox"
                      checked={acc.forward_enabled}
                      onChange={(e) => handleTogglePreference(acc.id, "forward_enabled", e.target.checked)}
                      className="accent-slate-500 rounded bg-slate-900 border-slate-700 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                    />
                    <span>📤 Forward</span>
                  </label>
                </div>

                <div className="flex items-end justify-between border-t border-slate-700/50 pt-3 mt-2.5">
                  <span className="text-[9px] text-slate-500">
                    Last Sync: {acc.last_sync ? new Date(acc.last_sync).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Never"}
                  </span>
                  
                  <button
                    onClick={() => handleDisconnect(acc.id)}
                    className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/15 focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition cursor-pointer"
                    title="Disconnect Mailbox"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Connect mailbox options */}
      <div className="border-t border-slate-700/50 pt-5">
        <h3 className="text-[10px] uppercase tracking-widest font-bold text-slate-400 mb-3 px-1 text-left">
          Add Connection Provider
        </h3>
        
        <div className="grid grid-cols-1 xs:grid-cols-3 gap-3">
          <button
            onClick={() => handleOAuthConnect("microsoft")}
            className="py-3 px-4 rounded-xl bg-slate-800 border border-slate-700 hover:border-blue-900/40 hover:bg-blue-950/10 text-slate-200 hover:text-blue-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm"
          >
            <div className="h-9 w-9 rounded-lg bg-blue-900/20 border border-blue-900/30 flex items-center justify-center text-blue-400 shadow-sm shrink-0">
              <Sparkles className="h-4.5 w-4.5" />
            </div>
            <span>Microsoft Exchange</span>
          </button>

          <button
            onClick={() => handleOAuthConnect("google")}
            className="py-3 px-4 rounded-xl bg-slate-800 border border-slate-700 hover:border-red-900/40 hover:bg-red-950/10 text-slate-200 hover:text-red-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm"
          >
            <div className="h-9 w-9 rounded-lg bg-red-950/50 border border-red-900/30 flex items-center justify-center text-red-400 shadow-sm shrink-0">
              <Mail className="h-4.5 w-4.5" />
            </div>
            <span>Google Gmail</span>
          </button>

          <button
            onClick={() => setShowImapDialog(true)}
            className="py-3 px-4 rounded-xl bg-slate-800 border border-slate-700 hover:border-indigo-900/40 hover:bg-indigo-950/10 text-slate-200 hover:text-indigo-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm"
          >
            <div className="h-9 w-9 rounded-lg bg-indigo-900/20 border border-indigo-900/30 flex items-center justify-center text-indigo-400 shadow-sm shrink-0">
              <Plus className="h-4.5 w-4.5" />
            </div>
            <span>Custom IMAP SSL</span>
          </button>
        </div>
      </div>

      {/* Custom IMAP Dialog Component inline to save files */}
      {showImapDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-card rounded-2xl p-6 w-full max-w-md border border-slate-700 shadow-2xl relative">
            <h3 className="text-sm font-bold text-white mb-1">Connect Custom IMAP</h3>
            <p className="text-xs text-slate-400 mb-5">
              Enter your email provider's secure IMAP credentials.
            </p>

            {imapError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-xs text-rose-300">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{imapError}</span>
              </div>
            )}

            <form onSubmit={handleImapConnect} className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={imapEmail}
                  onChange={(e) => setImapEmail(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                />
              </div>
              
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">App Password</label>
                <input
                  type="password"
                  required
                  value={imapPassword}
                  onChange={(e) => setImapPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">IMAP Host</label>
                  <input
                    type="text"
                    required
                    placeholder="imap.mail.com"
                    value={imapHost}
                    onChange={(e) => setImapHost(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Port</label>
                  <input
                    type="text"
                    required
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 text-center transition-shadow"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowImapDialog(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={imapConnecting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 text-white text-xs font-bold flex items-center space-x-2 transition cursor-pointer shadow shadow-sm shadow-black/10"
                >
                  {imapConnecting && <Loader2 className="h-3 w-3 animate-spin shrink-0" />}
                  <span>Connect</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
