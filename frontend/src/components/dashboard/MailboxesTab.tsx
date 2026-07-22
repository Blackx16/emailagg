import React, { useState } from "react";
import { Activity, BellRing, SlidersHorizontal, Loader2, Trash2, AlertCircle, Plus, Inbox, Bell, Send } from "lucide-react";
import { Account } from "../../types/dashboard";

/* ---- Official brand logos as inline SVGs ---- */
function MicrosoftOutlookLogo({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="-3.2 -3.2 38.40 38.40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="10" y="2" width="20" height="28" rx="2" fill="#1066B5"></rect>
      <rect x="10" y="2" width="20" height="28" rx="2" fill="url(#paint0_linear_87_7742)"></rect>
      <rect x="10" y="5" width="10" height="10" fill="#32A9E7"></rect>
      <rect x="10" y="15" width="10" height="10" fill="#167EB4"></rect>
      <rect x="20" y="15" width="10" height="10" fill="#32A9E7"></rect>
      <rect x="20" y="5" width="10" height="10" fill="#58D9FD"></rect>
      <mask id="mask0_87_7742" style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x="8" y="14" width="24" height="16">
        <path d="M8 14H30C31.1046 14 32 14.8954 32 16V28C32 29.1046 31.1046 30 30 30H10C8.89543 30 8 29.1046 8 28V14Z" fill="url(#paint1_linear_87_7742)"></path>
      </mask>
      <g mask="url(#mask0_87_7742)">
        <path d="M32 14V18H30V14H32Z" fill="#135298"></path>
        <path d="M32 30V16L7 30H32Z" fill="url(#paint2_linear_87_7742)"></path>
        <path d="M8 30V16L33 30H8Z" fill="url(#paint3_linear_87_7742)"></path>
      </g>
      <path d="M8 12C8 10.3431 9.34315 9 11 9H17C18.6569 9 20 10.3431 20 12V24C20 25.6569 18.6569 27 17 27H8V12Z" fill="#000000" fillOpacity="0.3"></path>
      <rect y="7" width="18" height="18" rx="2" fill="url(#paint4_linear_87_7742)"></rect>
      <path d="M14 16.0693V15.903C14 13.0222 11.9272 11 9.01582 11C6.08861 11 4 13.036 4 15.9307V16.097C4 18.9778 6.07278 21 9 21C11.9114 21 14 18.964 14 16.0693ZM11.6424 16.097C11.6424 18.0083 10.5665 19.1579 9.01582 19.1579C7.46519 19.1579 6.37342 17.9806 6.37342 16.0693V15.903C6.37342 13.9917 7.44937 12.8421 9 12.8421C10.5348 12.8421 11.6424 14.0194 11.6424 15.9307V16.097Z" fill="white"></path>
      <defs>
        <linearGradient id="paint0_linear_87_7742" x1="10" y1="16" x2="30" y2="16" gradientUnits="userSpaceOnUse">
          <stop stopColor="#064484"></stop>
          <stop offset="1" stopColor="#0F65B5"></stop>
        </linearGradient>
        <linearGradient id="paint1_linear_87_7742" x1="8" y1="26.7692" x2="32" y2="26.7692" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1B366F"></stop>
          <stop offset="1" stopColor="#2657B0"></stop>
        </linearGradient>
        <linearGradient id="paint2_linear_87_7742" x1="32" y1="23" x2="8" y2="23" gradientUnits="userSpaceOnUse">
          <stop stopColor="#44DCFD"></stop>
          <stop offset="0.453125" stopColor="#259ED0"></stop>
        </linearGradient>
        <linearGradient id="paint3_linear_87_7742" x1="8" y1="23" x2="32" y2="23" gradientUnits="userSpaceOnUse">
          <stop stopColor="#259ED0"></stop>
          <stop offset="1" stopColor="#44DCFD"></stop>
        </linearGradient>
        <linearGradient id="paint4_linear_87_7742" x1="0" y1="16" x2="18" y2="16" gradientUnits="userSpaceOnUse">
          <stop stopColor="#064484"></stop>
          <stop offset="1" stopColor="#0F65B5"></stop>
        </linearGradient>
      </defs>
    </svg>
  );
}

function GmailLogo({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
      <path d="M16.58,19.1068l-12.69-8.0757A3,3,0,0,1,7.1109,5.97l9.31,5.9243L24.78,6.0428A3,3,0,0,1,28.22,10.9579Z" fill="#ea4435"></path>
      <path d="M25.5,5.5h4a0,0,0,0,1,0,0v18a3,3,0,0,1-3,3h0a3,3,0,0,1-3-3V7.5a2,2,0,0,1,2-2Z" fill="#00ac47" transform="translate(53.0001 32.0007) rotate(180)"></path>
      <path d="M29.4562,8.0656c-.0088-.06-.0081-.1213-.0206-.1812-.0192-.0918-.0549-.1766-.0823-.2652a2.9312,2.9312,0,0,0-.0958-.2993c-.02-.0475-.0508-.0892-.0735-.1354A2.9838,2.9838,0,0,0,28.9686,6.8c-.04-.0581-.09-.1076-.1342-.1626a3.0282,3.0282,0,0,0-.2455-.2849c-.0665-.0647-.1423-.1188-.2146-.1771a3.02,3.02,0,0,0-.24-.1857c-.0793-.0518-.1661-.0917-.25-.1359-.0884-.0461-.175-.0963-.267-.1331-.0889-.0358-.1837-.0586-.2766-.0859s-.1853-.06-.2807-.0777a3.0543,3.0543,0,0,0-.357-.036c-.0759-.0053-.1511-.0186-.2273-.018a2.9778,2.9778,0,0,0-.4219.0425c-.0563.0084-.113.0077-.1689.0193a33.211,33.211,0,0,0-.5645.178c-.0515.022-.0966.0547-.1465.0795A2.901,2.901,0,0,0,23.5,8.5v5.762l4.72-3.3043a2.8878,2.8878,0,0,0,1.2359-2.8923Z" fill="#ffba00"></path>
      <path d="M5.5,5.5h0a3,3,0,0,1,3,3v18a0,0,0,0,1,0,0h-4a2,2,0,0,1-2-2V8.5a3,3,0,0,1,3-3Z" fill="#4285f4"></path>
      <path d="M2.5439,8.0656c.0088-.06.0081-.1213.0206-.1812.0192-.0918.0549-.1766.0823-.2652A2.9312,2.9312,0,0,1,2.7426,7.32c.02-.0475.0508-.0892.0736-.1354A2.9719,2.9719,0,0,1,3.0316,6.8c.04-.0581.09-.1076.1342-.1626a3.0272,3.0272,0,0,1,.2454-.2849c.0665-.0647.1423-.1188.2147-.1771a3.0005,3.0005,0,0,1,.24-.1857c.0793-.0518.1661-.0917.25-.1359A2.9747,2.9747,0,0,1,4.3829,5.72c.089-.0358.1838-.0586.2766-.0859s.1853-.06.2807-.0777a3.0565,3.0565,0,0,1,.357-.036c.076-.0053.1511-.0186.2273-.018a2.9763,2.9763,0,0,1,.4219.0425c.0563.0084.113.0077.169.0193a2.9056,2.9056,0,0,1,.286.0888,2.9157,2.9157,0,0,1,.2785.0892c.0514.022.0965.0547.1465.0795a2.9745,2.9745,0,0,1,.3742.21A2.9943,2.9943,0,0,1,8.5,8.5v5.762L3.78,10.9579A2.8891,2.8891,0,0,1,2.5439,8.0656Z" fill="#c52528"></path>
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
