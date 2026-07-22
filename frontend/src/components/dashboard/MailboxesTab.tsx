import React, { useState } from "react";
import { Activity, BellRing, SlidersHorizontal, Loader2, Trash2, AlertCircle, Plus, Inbox, Bell, Send } from "lucide-react";
import { Account } from "../../types/dashboard";

/* ---- Official brand logos as inline SVGs ---- */
function MicrosoftOutlookLogo({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2L2 6v12l10 4 10-4V6L12 2z" fill="#0078D4" opacity="0.15" />
      <path d="M22 8.5V17l-6 2.5V6l6 2.5z" fill="#0078D4" />
      <path d="M16 6v13.5l-6 2.5V3.5L16 6z" fill="#0078D4" opacity="0.7" />
      <path d="M10 3.5V22l-8-3.2V6.7L10 3.5z" fill="#0078D4" />
      <ellipse cx="6" cy="12.5" rx="3" ry="3.5" fill="white" />
    </svg>
  );
}

function GmailLogo({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 6l10 7L22 6v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" fill="#EA4335" opacity="0.15" />
      <path d="M22 6l-10 7L2 6" stroke="#EA4335" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="2" y="6" width="20" height="12" rx="2" stroke="#EA4335" strokeWidth="1.5" fill="none" />
    </svg>
  );
}

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
      const res = await fetch("/api/v1/accounts/imap", {
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 mb-2 rounded-xl glass border border-[var(--border)] divide-y lg:divide-y-0 lg:divide-x divide-[var(--border)] shadow-md">
        
        {/* Accounts limits */}
        <div className="flex flex-col justify-between text-left p-5">
          <div className="space-y-1 mb-4">
            <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
              Limit Tracking
            </h3>
            <p className="text-[10px] text-[var(--text-secondary)]">
              Plan boundaries governed by subscription.
            </p>
          </div>
          <div className="flex items-end justify-between mt-auto">
            <span className="text-2xl font-black text-[var(--text-primary)] leading-none tracking-tight">
              {activeAccounts.length}
            </span>
            <span className="text-xs text-[var(--text-tertiary)] font-bold mb-0.5">
              / {user?.plan === "free" ? 3 : user?.plan === "pro" ? 25 : 100} limit
            </span>
          </div>
        </div>

        {/* Notification Throttle */}
        <div className="flex flex-col text-left p-5 space-y-3 justify-between">
          <div>
            <div className="flex items-start justify-between mb-1">
              <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <BellRing className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
                Throttle
              </h3>
              <span className="text-[9px] text-[var(--text-tertiary)] bg-[var(--bg-surface)] border border-[var(--border)] px-1.5 py-0.5 rounded shrink-0 ml-2">
                <b className="text-indigo-500">{notifLimitEffective}</b>/hr effective
              </span>
            </div>
            <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
              Max Telegram alerts. Floor is <span className="text-indigo-500 font-bold">{notifLimitFloor}/hr</span>.
            </p>
          </div>
          <div className="flex items-center space-x-2 mt-auto pt-2">
            <input
              type="number"
              min={1}
              value={notifLimitInput}
              onChange={(e) => setNotifLimitInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveNotifLimit()}
              className="w-16 px-2 py-1.5 text-xs bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-indigo-500 text-center shadow-inner"
            />
            <button
              onClick={saveNotifLimit}
              disabled={notifLimitSaving}
              className="px-3 py-1.5 rounded-lg bg-[var(--accent-muted)] hover:bg-indigo-600/30 text-indigo-400 border border-indigo-500/30 text-[10px] font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition cursor-pointer disabled:opacity-50"
            >
              {notifLimitSaving ? "..." : "Save"}
            </button>
            {parseInt(notifLimitInput) < notifLimitFloor && (
              <span className="text-[9px] text-amber-500/80 ml-auto flex items-center"><AlertCircle className="w-3 h-3 mr-0.5"/>Floor</span>
            )}
          </div>
        </div>

        {/* Mass Controls — always horizontal */}
        <div className={`flex flex-col text-left p-5 justify-between ${activeAccounts.length === 0 ? "opacity-40" : ""}`}>
          <div>
            <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5 mb-1">
              <SlidersHorizontal className="h-3.5 w-3.5 text-[var(--text-tertiary)]" />
              Mass Controls
            </h3>
            <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
              {activeAccounts.length === 0 ? "No active mailboxes." : "Apply preferences to all active mailboxes."}
            </p>
          </div>
          
          {activeAccounts.length > 0 && (
            <div className="grid grid-cols-3 gap-2 text-xs font-semibold text-[var(--text-secondary)] mt-4 pt-3 border-t border-[var(--border)]">
              <label className="flex items-center space-x-2 cursor-pointer select-none group py-1" title="Dash Delivery for all">
                <input
                  type="checkbox"
                  checked={allDashEnabled}
                  onChange={(e) => handleMassTogglePreference("deliver_to_dashboard", e.target.checked)}
                  className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                />
                <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                  <Inbox className="w-3.5 h-3.5 mr-1" />
                  <span>Dash</span>
                </div>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer select-none group py-1" title="Telegram Alerts for all">
                <input
                  type="checkbox"
                  checked={allAlertsEnabled}
                  onChange={(e) => handleMassTogglePreference("notify_telegram", e.target.checked)}
                  className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                />
                <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                  <Bell className="w-3.5 h-3.5 mr-1" />
                  <span>Alerts</span>
                </div>
              </label>

              <label className="flex items-center space-x-2 cursor-pointer select-none group py-1" title="Email Forwarding for all">
                <input
                  type="checkbox"
                  checked={allForwardEnabled}
                  onChange={(e) => handleMassTogglePreference("forward_enabled", e.target.checked)}
                  className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                />
                <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                  <Send className="w-3.5 h-3.5 mr-1" />
                  <span>Fwd</span>
                </div>
              </label>
            </div>
          )}
        </div>
      </div>

      {/* List of Connected Mailboxes */}
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
          Connected Mailboxes
        </h2>

        {activeAccounts.length === 0 ? (
          <div className="p-8 text-center glass-card rounded-xl border border-[var(--border)] text-[var(--text-secondary)] text-xs mb-6">
            No active mailboxes connected. Add an account below to begin.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {activeAccounts.map((acc) => (
              <div key={acc.id} className="p-4 rounded-xl glass-card text-left border border-[var(--border)] flex flex-col justify-between min-h-[175px]">
                <div className="flex items-start justify-between">
                  <div>
                    <span className={`text-[8px] uppercase tracking-widest font-black px-1.5 py-0.5 rounded ${
                      acc.provider === "microsoft" ? "bg-blue-950/60 border border-blue-900/40 text-blue-400" :
                      acc.provider === "google" ? "bg-red-950/60 border border-red-900/40 text-red-400" :
                      "bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-secondary)]"
                    }`}>
                      {acc.provider}
                    </span>
                    <h4 className="text-xs font-bold text-[var(--text-primary)] mt-2.5 truncate max-w-[200px]" title={acc.email}>
                      {acc.email}
                    </h4>
                  </div>

                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center ${
                    acc.status === "active" ? "bg-emerald-900/20 border border-emerald-900/30 text-emerald-400" :
                    acc.status === "syncing" ? "bg-indigo-900/20 border border-indigo-900/30 text-indigo-400" :
                    acc.status === "error" ? "bg-rose-900/20 border border-rose-900/30 text-rose-400 animate-pulse" :
                    "bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-secondary)]"
                  }`}>
                    {acc.status === "syncing" && <Loader2 className="h-3 w-3 animate-spin mr-1 text-indigo-400 shrink-0" />}
                    {acc.status === "active" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1.5 shrink-0" />}
                    {acc.status === "error" && <AlertCircle className="h-3 w-3 mr-1 text-rose-400 shrink-0" />}
                    {acc.status.toUpperCase()}
                  </span>
                </div>

                {/* Preferences Toggles — always horizontal */}
                <div className="mt-4 pt-3 border-t border-[var(--border)] grid grid-cols-3 gap-2 text-[10px] font-semibold text-[var(--text-secondary)]">
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none py-1 group" title="Show incoming emails on dashboard">
                    <input
                      type="checkbox"
                      checked={acc.deliver_to_dashboard}
                      onChange={(e) => handleTogglePreference(acc.id, "deliver_to_dashboard", e.target.checked)}
                      className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                    />
                    <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                      <Inbox className="w-3.5 h-3.5 mr-1" />
                      <span>Dash</span>
                    </div>
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none py-1 group" title="Send alerts to your Telegram bot">
                    <input
                      type="checkbox"
                      checked={acc.notify_telegram}
                      onChange={(e) => handleTogglePreference(acc.id, "notify_telegram", e.target.checked)}
                      className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                    />
                    <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                      <Bell className="w-3.5 h-3.5 mr-1" />
                      <span>Alerts</span>
                    </div>
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer select-none py-1 group" title="Enable custom email forwarding rules">
                    <input
                      type="checkbox"
                      checked={acc.forward_enabled}
                      onChange={(e) => handleTogglePreference(acc.id, "forward_enabled", e.target.checked)}
                      className="accent-indigo-500 rounded bg-[var(--bg-surface)] border-[var(--border)] focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                    />
                    <div className="flex items-center group-hover:text-[var(--text-primary)] transition-colors">
                      <Send className="w-3.5 h-3.5 mr-1" />
                      <span>Forward</span>
                    </div>
                  </label>
                </div>

                <div className="flex items-end justify-between border-t border-[var(--border)] pt-3 mt-2.5">
                  <span className="text-[9px] text-[var(--text-tertiary)]">
                    Last Sync: {acc.last_sync ? new Date(acc.last_sync).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Never"}
                  </span>
                  
                  <button
                    onClick={() => handleDisconnect(acc.id)}
                    className="p-1.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/15 focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition cursor-pointer"
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

      {/* Add Mailbox — redesigned with official logos */}
      <div className="border-t border-[var(--border)] pt-6">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">
          Add Mailbox
        </h2>
        
        <div className="grid grid-cols-1 xs:grid-cols-3 gap-3">
          <button
            onClick={() => handleOAuthConnect("microsoft")}
            className="py-4 px-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] text-xs font-semibold flex flex-col items-center justify-center space-y-2.5 transition cursor-pointer group"
          >
            <MicrosoftOutlookLogo className="h-10 w-10 group-hover:scale-105 transition-transform" />
            <span>Microsoft Outlook</span>
          </button>

          <button
            onClick={() => handleOAuthConnect("google")}
            className="py-4 px-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] text-xs font-semibold flex flex-col items-center justify-center space-y-2.5 transition cursor-pointer group"
          >
            <GmailLogo className="h-10 w-10 group-hover:scale-105 transition-transform" />
            <span>Google Gmail</span>
          </button>

          <button
            onClick={() => setShowImapDialog(true)}
            className="py-4 px-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] text-[var(--text-primary)] text-xs font-semibold flex flex-col items-center justify-center space-y-2.5 transition cursor-pointer group"
          >
            <div className="h-10 w-10 rounded-lg bg-[var(--accent-muted)] border border-indigo-500/20 flex items-center justify-center text-indigo-500 group-hover:scale-105 transition-transform">
              <Plus className="h-5 w-5" />
            </div>
            <span>Custom IMAP SSL</span>
          </button>
        </div>
      </div>

      {/* Custom IMAP Dialog */}
      {showImapDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="glass-card rounded-2xl p-6 w-full max-w-md border border-[var(--border-strong)] shadow-2xl relative">
            <h3 className="text-sm font-bold text-[var(--text-primary)] mb-1">Connect Custom IMAP</h3>
            <p className="text-xs text-[var(--text-secondary)] mb-5">
              Enter your email provider's secure IMAP credentials.
            </p>

            {imapError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-xs text-rose-400">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{imapError}</span>
              </div>
            )}

            <form onSubmit={handleImapConnect} className="space-y-4">
              <div>
                <label className="block text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={imapEmail}
                  onChange={(e) => setImapEmail(e.target.value)}
                  className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                />
              </div>
              
              <div>
                <label className="block text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-1">App Password</label>
                <input
                  type="password"
                  required
                  value={imapPassword}
                  onChange={(e) => setImapPassword(e.target.value)}
                  className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-1">IMAP Host</label>
                  <input
                    type="text"
                    required
                    placeholder="imap.mail.com"
                    value={imapHost}
                    onChange={(e) => setImapHost(e.target.value)}
                    className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 transition-shadow"
                  />
                </div>
                <div className="col-span-1">
                  <label className="block text-[10px] uppercase font-bold text-[var(--text-secondary)] mb-1">Port</label>
                  <input
                    type="text"
                    required
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 text-center transition-shadow"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowImapDialog(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition cursor-pointer"
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
