"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/api";
import { 
  Inbox, 
  Settings, 
  Mail, 
  Plus, 
  Trash2, 
  RefreshCw, 
  LogOut, 
  User as UserIcon, 
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Loader2,
  Clock,
  Sparkles,
  ArrowRight,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
  Sliders
} from "lucide-react";

interface Account {
  id: string;
  provider: "microsoft" | "google" | "imap";
  email: string;
  status: "active" | "syncing" | "error" | "disconnected";
  last_sync: string | null;
  error_message: string | null;
  notify_telegram: boolean;
  deliver_to_dashboard: boolean;
  forward_enabled: boolean;
}

interface EmailItem {
  id: string;
  mail_account_id: string;
  message_id: string;
  subject: string | null;
  from_email: string | null;
  from_name: string | null;
  received_at: string | null;
  snippet: string | null;
  has_attachment: boolean;
  is_read: boolean;
  body_html?: string | null;
  body_text?: string | null;
}

export default function DashboardPage() {
  const { user, token, loading, error, isTelegramWebApp, tgWebApp, loginManual, logout } = useAuth();
  
  // Dev login states
  const [devTelegramId, setDevTelegramId] = useState("");
  const [devLoginLoading, setDevLoginLoading] = useState(false);
  const [devLoginError, setDevLoginError] = useState<string | null>(null);
  
  // Tab states: "inbox" | "mailboxes" | "rules"
  const [activeTab, setActiveTab] = useState<"inbox" | "mailboxes" | "rules">("inbox");

  // Read initial tab from URL parameters or hash
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "rules" || tabParam === "mailboxes" || tabParam === "inbox") {
        setActiveTab(tabParam);
      } else if (window.location.hash === "#rules") {
        setActiveTab("rules");
      }
    }
  }, []);

  // Rules Engine states
  const [rules, setRules] = useState<any[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);
  const [showAddRuleForm, setShowAddRuleForm] = useState(false);
  const [newRuleScope, setNewRuleScope] = useState<string>("global");
  const [newRuleSubject, setNewRuleSubject] = useState("");
  const [newRuleFromDomain, setNewRuleFromDomain] = useState("");
  const [newRuleFromEmail, setNewRuleFromEmail] = useState("");
  const [newRuleBody, setNewRuleBody] = useState("");
  const [newRuleTarget, setNewRuleTarget] = useState("");
  const [ruleSubmitting, setRuleSubmitting] = useState(false);
  
  // Core data states
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  
  // Search & Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "unread" | "read">("all");
  const [providerFilter, setProviderFilter] = useState<"all" | "microsoft" | "google" | "imap">("all");
  const [mailboxFilter, setMailboxFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [totalEmails, setTotalEmails] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  
  // Email detail state
  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(null);
  const [emailDetailLoading, setEmailDetailLoading] = useState(false);
  const [emailDetail, setEmailDetail] = useState<any | null>(null);
  const [emailBodyView, setEmailBodyView] = useState<"html" | "text">("html");
  
  // IMAP connect dialog state
  const [showImapDialog, setShowImapDialog] = useState(false);
  const [imapEmail, setImapEmail] = useState("");
  const [imapPassword, setImapPassword] = useState("");
  const [imapHost, setImapHost] = useState("");
  const [imapPort, setImapPort] = useState("993");
  const [imapConnecting, setImapConnecting] = useState(false);
  const [imapError, setImapError] = useState<string | null>(null);

  // Notification limit preferences
  const [notifLimit, setNotifLimit] = useState<number>(20);
  const [notifLimitFloor, setNotifLimitFloor] = useState<number>(5);
  const [notifLimitEffective, setNotifLimitEffective] = useState<number>(20);
  const [notifLimitSaving, setNotifLimitSaving] = useState(false);
  const [notifLimitInput, setNotifLimitInput] = useState<string>("20");

  // Fetch accounts and emails
  const fetchData = async (
    isRefresh = false, 
    pageOverride?: number, 
    statusOverride?: string, 
    providerOverride?: string, 
    mailboxOverride?: string, 
    searchOverride?: string
  ) => {
    if (!token) return;
    
    if (isRefresh) setRefreshing(true);
    else setDataLoading(true);
    
    try {
      // 1. Fetch connected mail accounts
      const accountsData = await apiFetch("/api/v1/accounts", { token });
      setAccounts(accountsData);
      
      // 2. Build email query parameters
      const queryPage = pageOverride !== undefined ? pageOverride : page;
      const queryStatus = statusOverride !== undefined ? statusOverride : statusFilter;
      const queryProvider = providerOverride !== undefined ? providerOverride : providerFilter;
      const queryMailbox = mailboxOverride !== undefined ? mailboxOverride : mailboxFilter;
      const querySearch = searchOverride !== undefined ? searchOverride : activeSearch;

      let urlParams = new URLSearchParams();
      urlParams.append("page", queryPage.toString());
      urlParams.append("limit", limit.toString());

      if (queryStatus === "unread") urlParams.append("is_read", "false");
      if (queryStatus === "read") urlParams.append("is_read", "true");
      if (queryProvider !== "all") urlParams.append("provider", queryProvider);
      if (queryMailbox !== "all") urlParams.append("account_id", queryMailbox);
      if (querySearch.trim() !== "") urlParams.append("search", querySearch.trim());

      const emailsData = await apiFetch(`/api/v1/emails?${urlParams.toString()}`, { token });
      setEmails(emailsData.emails || []);
      setTotalEmails(emailsData.total || 0);
      setTotalPages(emailsData.total_pages || 0);
      
      if (pageOverride !== undefined) setPage(pageOverride);
    } catch (err: any) {
      console.error("Error fetching dashboard data:", err);
    } finally {
      setDataLoading(false);
      setRefreshing(false);
    }
  };

  // Reset page and fetch data when filters or search change
  useEffect(() => {
    if (token) {
      setPage(1);
      fetchData(false, 1, statusFilter, providerFilter, mailboxFilter, activeSearch);
    }
  }, [token, statusFilter, providerFilter, mailboxFilter, activeSearch]);

  // Fetch when page changes
  useEffect(() => {
    if (token && page !== 1) {
      fetchData(false, page, statusFilter, providerFilter, mailboxFilter, activeSearch);
    }
  }, [page]);

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return;
    setPage(newPage);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setActiveSearch("");
  };

  // Dev login trigger
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

  // Disconnect mailbox
  const handleDisconnect = async (accountId: string) => {
    if (!confirm("Are you sure you want to disconnect this mailbox? This will delete all cached emails for this account.")) return;
    try {
      await apiFetch(`/api/v1/auth/disconnect/${accountId}`, {
        method: "POST",
        token,
      });
      // Refresh list
      fetchData();
    } catch (err: any) {
      alert(`Failed to disconnect: ${err.message}`);
    }
  };

  // Fetch notification preferences
  const fetchNotifPrefs = async () => {
    if (!token) return;
    try {
      const data = await apiFetch("/api/v1/users/me/preferences", { token });
      setNotifLimit(data.notification_limit_per_hour);
      setNotifLimitInput(String(data.notification_limit_per_hour));
      setNotifLimitFloor(data.floor);
      setNotifLimitEffective(data.effective_limit);
    } catch (err) {
      console.error("Failed to fetch notification prefs:", err);
    }
  };

  const saveNotifLimit = async () => {
    const val = parseInt(notifLimitInput, 10);
    if (isNaN(val) || val < 1) return;
    setNotifLimitSaving(true);
    try {
      const data = await apiFetch("/api/v1/users/me/preferences", {
        token,
        method: "PUT",
        body: { notification_limit_per_hour: val },
      });
      setNotifLimit(data.notification_limit_per_hour);
      setNotifLimitInput(String(data.notification_limit_per_hour));
      setNotifLimitFloor(data.floor);
      setNotifLimitEffective(data.effective_limit);
    } catch (err) {
      console.error("Failed to save notification limit:", err);
    } finally {
      setNotifLimitSaving(false);
    }
  };

  const handleTogglePreference = async (
    accountId: string,
    key: "notify_telegram" | "deliver_to_dashboard" | "forward_enabled",
    value: boolean
  ) => {
    // Optimistic update
    setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, [key]: value } : a));

    try {
      const account = accounts.find(a => a.id === accountId);
      if (!account) return;

      const body = {
        notify_telegram: key === "notify_telegram" ? value : account.notify_telegram,
        deliver_to_dashboard: key === "deliver_to_dashboard" ? value : account.deliver_to_dashboard,
        forward_enabled: key === "forward_enabled" ? value : account.forward_enabled,
      };

      await apiFetch(`/api/v1/accounts/${accountId}/preferences`, {
        method: "PUT",
        token,
        body,
      });
    } catch (err: any) {
      console.error("Failed to update preferences:", err);
      // Rollback on error
      const originalAccount = accounts.find(a => a.id === accountId);
      if (originalAccount) {
        setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, [key]: originalAccount[key] } : a));
      }
      alert(err.message || "Failed to update preferences.");
    }
  };

  const handleMassTogglePreference = async (
    key: "notify_telegram" | "deliver_to_dashboard" | "forward_enabled",
    value: boolean
  ) => {
    const activeAccounts = accounts.filter(a => a.status !== "disconnected");
    if (activeAccounts.length === 0) return;

    // Optimistic update
    setAccounts(prev => prev.map(a => a.status !== "disconnected" ? { ...a, [key]: value } : a));

    try {
      await Promise.all(
        activeAccounts.map(account => {
          const body = {
            notify_telegram: key === "notify_telegram" ? value : account.notify_telegram,
            deliver_to_dashboard: key === "deliver_to_dashboard" ? value : account.deliver_to_dashboard,
            forward_enabled: key === "forward_enabled" ? value : account.forward_enabled,
          };
          return apiFetch(`/api/v1/accounts/${account.id}/preferences`, {
            method: "PUT",
            token,
            body,
          });
        })
      );
    } catch (err: any) {
      console.error(`Failed to update mass preferences for ${key}:`, err);
      // Revert fetch on error
      fetchData(false);
      alert(err.message || "Failed to update all preferences.");
    }
  };

  // Rules CRUD Handlers
  const fetchRules = async () => {
    if (!token) return;
    setRulesLoading(true);
    try {
      const data = await apiFetch("/api/v1/rules", { token });
      setRules(data);
    } catch (err: any) {
      console.error("Failed to fetch rules:", err);
    } finally {
      setRulesLoading(false);
    }
  };

  useEffect(() => {
    if (token && activeTab === "mailboxes") {
      fetchNotifPrefs();
    }
    if (token && activeTab === "rules") {
      fetchRules();
    }
  }, [token, activeTab]);


  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRuleTarget) return;
    setRuleSubmitting(true);
    try {
      const body = {
        mail_account_id: newRuleScope === "global" ? null : newRuleScope,
        condition_subject_contains: newRuleSubject || null,
        condition_from_domain: newRuleFromDomain || null,
        condition_from_email: newRuleFromEmail || null,
        condition_body_contains: newRuleBody || null,
        forward_to_email: newRuleTarget,
        is_active: true
      };
      const newRule = await apiFetch("/api/v1/rules", {
        method: "POST",
        token,
        body
      });
      setRules(prev => [newRule, ...prev]);
      setShowAddRuleForm(false);
      // Clear form
      setNewRuleSubject("");
      setNewRuleFromDomain("");
      setNewRuleFromEmail("");
      setNewRuleBody("");
      setNewRuleTarget("");
    } catch (err: any) {
      alert(err.message || "Failed to create rule.");
    } finally {
      setRuleSubmitting(false);
    }
  };

  const handleToggleRuleActive = async (ruleId: string, value: boolean) => {
    setRules(prev => prev.map(r => r.id === ruleId ? { ...r, is_active: value } : r));
    try {
      const rule = rules.find(r => r.id === ruleId);
      if (!rule) return;
      const body = {
        mail_account_id: rule.mail_account_id,
        condition_subject_contains: rule.condition_subject_contains,
        condition_from_domain: rule.condition_from_domain,
        condition_from_email: rule.condition_from_email,
        condition_body_contains: rule.condition_body_contains,
        forward_to_email: rule.forward_to_email,
        is_active: value
      };
      await apiFetch(`/api/v1/rules/${ruleId}`, {
        method: "PUT",
        token,
        body
      });
    } catch (err: any) {
      // Rollback
      setRules(prev => prev.map(r => r.id === ruleId ? { ...r, is_active: !value } : r));
      alert(err.message || "Failed to update rule.");
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm("Are you sure you want to delete this forwarding rule?")) return;
    try {
      await apiFetch(`/api/v1/rules/${ruleId}`, {
        method: "DELETE",
        token
      });
      setRules(prev => prev.filter(r => r.id !== ruleId));
    } catch (err: any) {
      alert(err.message || "Failed to delete rule.");
    }
  };

  // Connect IMAP submit
  const handleImapConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setImapConnecting(true);
    setImapError(null);
    
    try {
      const portInt = parseInt(imapPort);
      if (isNaN(portInt)) {
        throw new Error("Port must be a valid number.");
      }
      
      await apiFetch("/api/v1/auth/imap/connect", {
        method: "POST",
        token,
        body: JSON.stringify({
          email: imapEmail,
          password: imapPassword,
          imap_host: imapHost,
          imap_port: portInt
        })
      });
      
      // Clear states & close dialog
      setImapEmail("");
      setImapPassword("");
      setImapHost("");
      setImapPort("993");
      setShowImapDialog(false);
      
      // Refresh accounts list
      fetchData();
    } catch (err: any) {
      setImapError(err.message || "Failed to connect IMAP account.");
    } finally {
      setImapConnecting(false);
    }
  };

  // Trigger OAuth redirects
  const handleOAuthConnect = (provider: "microsoft" | "google") => {
    if (!user) return;
    
    const backendOAuthUrl = `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://lvh.me:8000"}/api/v1/auth/${provider}/login?telegram_id=${user.telegram_id}`;
    
    if (isTelegramWebApp && tgWebApp && tgWebApp.openLink) {
      // Use Telegram's link opener inside WebApp
      tgWebApp.openLink(backendOAuthUrl);
    } else {
      // Direct redirect for browser fallback
      window.open(backendOAuthUrl, "_blank");
    }
  };

  // Fetch single email detail
  const handleSelectEmail = async (email: EmailItem) => {
    setSelectedEmail(email);
    setEmailDetailLoading(true);
    setEmailDetail(null);
    setEmailBodyView("html"); // Reset view on new email
    try {
      const details = await apiFetch(`/api/v1/emails/${email.id}`, { token });
      setEmailDetail(details);
    } catch (err: any) {
      console.error("Error loading email details:", err);
    } finally {
      setEmailDetailLoading(false);
    }
  };

  // Render loading screen
  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#090a0f] text-slate-100 p-6">
        <div className="p-8 rounded-2xl glass-card flex flex-col items-center max-w-sm w-full text-center border border-slate-800">
          {error ? (
            <>
              <AlertCircle className="h-10 w-10 text-rose-500 mb-4 animate-bounce" />
              <h2 className="text-lg font-bold tracking-wide text-white mb-2">Initialization Error</h2>
              <p className="text-xs text-rose-300 mb-5 leading-relaxed">{error}</p>
              <button
                onClick={() => {
                  try {
                    localStorage.clear();
                  } catch (e) {}
                  window.location.reload();
                }}
                className="w-full py-2 px-4 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-850 rounded-lg text-xs font-semibold text-white transition duration-200 cursor-pointer"
              >
                Clear Cache & Retry
              </button>
            </>
          ) : (
            <>
              <Loader2 className="h-10 w-10 text-indigo-500 animate-spin mb-4" />
              <h2 className="text-xl font-semibold tracking-wide text-white mb-2">Syncing Command Center</h2>
              <p className="text-xs text-slate-400">Loading Telegram WebApp session...</p>
            </>
          )}
        </div>
      </div>
    );
  }

  // Render Dev/Fallback Login Page if user is not authenticated (runs outside Telegram WebApp)
  if (!user || !token) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#090a0f]">
        {/* Glow backdrop decorative bubbles */}
        <div className="absolute top-1/4 left-1/4 h-80 w-80 rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" />
        <div className="absolute bottom-1/3 right-1/4 h-80 w-80 rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none" />

        <div className="max-w-md w-full glass-card rounded-2xl p-8 shadow-2xl relative border border-slate-800">
          <div className="flex justify-center mb-5">
            <div className="h-14 w-14 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg glow-indigo">
              <Mail className="h-7 w-7 text-white" />
            </div>
          </div>
          
          <h1 className="text-2xl font-bold text-center text-white tracking-wide mb-1">
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
          <div className="mb-6 p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs leading-relaxed text-slate-300">
            <div className="flex items-center space-x-1.5 font-semibold text-cyan-400">
              <ShieldCheck className="h-4 w-4" />
              <span>Telegram Web App Access</span>
            </div>
            <p>
              This dashboard is designed to run natively inside your Telegram Bot client. Message the bot and tap the menu to open this app.
            </p>
          </div>

          <form onSubmit={handleDevLogin} className="space-y-4 border-t border-slate-800/80 pt-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center">
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
                className="w-full px-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-lg text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {devLoginError && (
              <p className="text-xs text-rose-400">{devLoginError}</p>
            )}

            <button
              type="submit"
              disabled={devLoginLoading}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition duration-200 cursor-pointer shadow-md shadow-indigo-950/50"
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
        </div>
      </div>
    );
  }

  // Render Premium Dashboard layout when logged in
  return (
    <div className="flex-1 flex flex-col bg-[#090a0f] text-slate-100 min-h-screen">
      
      {/* Header bar */}
      <header className="sticky top-0 z-30 glass border-b border-slate-900 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center glow-indigo shadow-md">
            <Mail className="h-4.5 w-4.5 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide">EmailAgg</h2>
            <p className="text-[10px] text-slate-400">Telegram Command Center</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden xs:flex flex-col items-end mr-1">
            <div className="flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-semibold text-slate-300">ID: {user.telegram_id}</span>
            </div>
            <span className="text-[9px] uppercase tracking-widest font-black text-cyan-400 bg-cyan-950/50 border border-cyan-800/40 px-1.5 rounded">
              {user.plan} plan
            </span>
          </div>

          <button 
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 hover:bg-slate-850 transition duration-150 cursor-pointer"
            title="Refresh Data"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-sync text-indigo-400" : ""}`} />
          </button>

          <button
            onClick={logout}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/10 transition duration-150 cursor-pointer"
            title="Log Out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Tabs Switcher */}
      <div className="p-4 pb-2 max-w-4xl w-full mx-auto">
        <div className="grid grid-cols-3 p-1 bg-slate-950/80 border border-slate-900 rounded-xl">
          <button
            onClick={() => { setActiveTab("inbox"); setSelectedEmail(null); }}
            className={`py-2 px-3 flex items-center justify-center space-x-2 text-xs font-semibold rounded-lg transition duration-200 cursor-pointer ${
              activeTab === "inbox"
                ? "bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow-md glow-indigo"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Inbox className="h-4 w-4" />
            <span>📩 Inbox</span>
          </button>
          <button
            onClick={() => { setActiveTab("mailboxes"); setSelectedEmail(null); }}
            className={`py-2 px-3 flex items-center justify-center space-x-2 text-xs font-semibold rounded-lg transition duration-200 cursor-pointer ${
              activeTab === "mailboxes"
                ? "bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow-md glow-indigo"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Settings className="h-4 w-4" />
            <span>⚙️ Mailboxes ({accounts.filter(a => a.status !== "disconnected").length})</span>
          </button>
          <button
            onClick={() => { setActiveTab("rules"); setSelectedEmail(null); }}
            className={`py-2 px-3 flex items-center justify-center space-x-2 text-xs font-semibold rounded-lg transition duration-200 cursor-pointer ${
              activeTab === "rules"
                ? "bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow-md glow-indigo"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sliders className="h-4 w-4" />
            <span>📤 Rules</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-4 max-w-4xl w-full mx-auto pb-10">
        
        {dataLoading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-3" />
            <p className="text-xs text-slate-400">Loading your inbox data...</p>
          </div>
        )}

        {!dataLoading && activeTab === "inbox" && (
          <div className="space-y-4">
            
            {/* Search and Filters Toolbar */}
            <div className="p-4 rounded-2xl glass border border-slate-900/60 space-y-3">
              <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
                
                {/* Search Input */}
                <form onSubmit={handleSearchSubmit} className="flex-1 relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search sender, subject, content..."
                    className="w-full pl-9 pr-8 py-2 bg-slate-950/80 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={handleClearSearch}
                      className="absolute right-3 top-2 text-slate-500 hover:text-slate-300 text-xs font-bold"
                    >
                      ✕
                    </button>
                  )}
                </form>

                {/* Filters Row */}
                <div className="flex flex-wrap gap-2 items-center">
                  {/* Read/Unread Filter */}
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as any)}
                    className="px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-[10px] sm:text-xs text-slate-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option value="all">📩 All Statuses</option>
                    <option value="unread">🔵 Unread Only</option>
                    <option value="read">📖 Read Only</option>
                  </select>

                  {/* Provider Filter */}
                  <select
                    value={providerFilter}
                    onChange={(e) => {
                      setProviderFilter(e.target.value as any);
                      setMailboxFilter("all");
                    }}
                    className="px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-[10px] sm:text-xs text-slate-300 focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    <option value="all">🌐 All Providers</option>
                    <option value="microsoft">Ⓜ️ Microsoft</option>
                    <option value="google"> G Google</option>
                    <option value="imap">🔌 IMAP</option>
                  </select>

                  {/* Specific Mailbox Filter */}
                  <select
                    value={mailboxFilter}
                    onChange={(e) => setMailboxFilter(e.target.value)}
                    className="px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-[10px] sm:text-xs text-slate-300 focus:outline-none focus:border-indigo-500 max-w-[150px] truncate cursor-pointer"
                  >
                    <option value="all">📬 All Mailboxes</option>
                    {accounts
                      .filter(a => a.status !== "disconnected")
                      .filter(a => providerFilter === "all" || a.provider === providerFilter)
                      .map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.email}
                        </option>
                      ))}
                  </select>
                </div>
              </div>
            </div>

            {/* If inbox is empty */}
            {emails.length === 0 ? (
              <div className="text-center py-16 px-6 glass-card rounded-2xl border border-slate-900">
                <div className="h-12 w-12 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto mb-4">
                  <Inbox className="h-6 w-6 text-slate-500" />
                </div>
                {activeSearch || statusFilter !== "all" || providerFilter !== "all" || mailboxFilter !== "all" ? (
                  <>
                    <h3 className="text-sm font-bold text-white mb-1">No matching emails</h3>
                    <p className="text-xs text-slate-400 max-w-xs mx-auto mb-5">
                      No emails match your active search term or filter selection.
                    </p>
                    <button
                      onClick={() => {
                        setSearchQuery("");
                        setActiveSearch("");
                        setStatusFilter("all");
                        setProviderFilter("all");
                        setMailboxFilter("all");
                      }}
                      className="inline-flex items-center space-x-1.5 py-1.5 px-3.5 bg-slate-900 border border-slate-800 hover:border-slate-700 text-white text-xs font-semibold rounded-lg transition cursor-pointer"
                    >
                      Clear Filters
                    </button>
                  </>
                ) : (
                  <>
                    <h3 className="text-sm font-bold text-white mb-1">No emails yet</h3>
                    <p className="text-xs text-slate-400 max-w-xs mx-auto mb-5">
                      Aggegated emails will appear here as soon as they arrive in your connected inboxes.
                    </p>
                    {accounts.filter(a => a.status === "active").length === 0 && (
                      <button
                        onClick={() => setActiveTab("mailboxes")}
                        className="inline-flex items-center space-x-1.5 py-1.5 px-3.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition cursor-pointer"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>Connect your first mailbox</span>
                      </button>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-start">
                
                {/* List of emails (takes full screen on mobile, left side on tablet/desktop) */}
                <div className={`space-y-2 md:col-span-3 ${selectedEmail ? "hidden md:block" : "block"}`}>
                  <h3 className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-2 px-1">
                    Aggegated Emails
                  </h3>
                  
                  <div className="space-y-2 overflow-y-auto max-h-[70vh] pr-1">
                    {emails.map((email) => {
                      const dateObj = email.received_at ? new Date(email.received_at) : null;
                      const formattedTime = dateObj ? dateObj.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
                      const accountEmail = accounts.find(a => a.id === email.mail_account_id)?.email || "";
                      
                      return (
                        <div
                          key={email.id}
                          onClick={() => handleSelectEmail(email)}
                          className={`p-3.5 rounded-xl cursor-pointer text-left glass glass-interactive border ${
                            selectedEmail?.id === email.id
                              ? "bg-slate-900/90 border-indigo-500/50 shadow-md shadow-indigo-950/20"
                              : "border-slate-900/50"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-xs font-bold text-slate-100 truncate max-w-[150px]">
                              {email.from_name || email.from_email || "Unknown Sender"}
                            </span>
                            <span className="text-[9px] text-slate-400 flex items-center shrink-0">
                              <Clock className="h-3 w-3 mr-0.5 shrink-0" />
                              {formattedTime}
                            </span>
                          </div>
                          
                          <h4 className="text-xs font-semibold text-slate-200 truncate mb-1">
                            {email.subject || "(No Subject)"}
                          </h4>
                          
                          <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed mb-2">
                            {email.snippet || "No preview snippet available."}
                          </p>

                          <div className="flex items-center justify-between border-t border-slate-900/80 pt-2 text-[8px] tracking-wider uppercase font-bold text-slate-500">
                            <span>Inbox: {accountEmail}</span>
                            {email.has_attachment && (
                              <span className="bg-slate-950/50 border border-slate-800 px-1 rounded text-cyan-400">
                                📎 Attachment
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Pagination controls */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-slate-900/80 pt-4 mt-4 text-xs text-slate-400 px-1">
                      <span>
                        Showing {(page - 1) * limit + 1} - {Math.min(page * limit, totalEmails)} of {totalEmails}
                      </span>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handlePageChange(page - 1)}
                          disabled={page === 1}
                          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <span className="px-3 font-semibold text-slate-200">
                          Page {page} of {totalPages}
                        </span>
                        <button
                          onClick={() => handlePageChange(page + 1)}
                          disabled={page === totalPages}
                          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Email details view (full view on mobile when open, right side on desktop) */}
                <div className={`md:col-span-2 space-y-2 ${selectedEmail ? "block" : "hidden md:block"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-[10px] uppercase tracking-wider font-bold text-slate-400 px-1">
                      Email Details
                    </h3>
                    {selectedEmail && (
                      <button
                        onClick={() => setSelectedEmail(null)}
                        className="md:hidden py-1 px-2.5 bg-slate-900 border border-slate-800 text-slate-300 text-[10px] font-bold rounded-lg cursor-pointer"
                      >
                        ← Back to list
                      </button>
                    )}
                  </div>

                  <div className="p-5 glass-card rounded-2xl text-left border border-slate-900 min-h-[40vh] flex flex-col">
                    {!selectedEmail ? (
                      <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                        <Mail className="h-8 w-8 text-slate-600 mb-2" />
                        <p className="text-xs text-slate-500">Select an email from the inbox list to read the message.</p>
                      </div>
                    ) : emailDetailLoading ? (
                      <div className="flex-1 flex flex-col items-center justify-center">
                        <Loader2 className="h-6 w-6 text-indigo-500 animate-spin mb-2" />
                        <p className="text-[10px] text-slate-500">Retrieving full message details...</p>
                      </div>
                    ) : (
                      <div className="space-y-4 flex-1 flex flex-col">
                        <div>
                          <span className="text-[9px] uppercase tracking-wider font-black text-cyan-400 bg-cyan-950/50 border border-cyan-900/40 px-1.5 py-0.5 rounded">
                            {accounts.find(a => a.id === selectedEmail.mail_account_id)?.provider || "IMAP"}
                          </span>
                          <h1 className="text-sm font-bold text-white mt-2 leading-snug">
                            {selectedEmail.subject || "(No Subject)"}
                          </h1>
                        </div>

                        <div className="border-y border-slate-900 py-3 text-xs space-y-1.5 leading-relaxed text-slate-300">
                          <div>
                            <span className="font-bold text-slate-400">From:</span> {selectedEmail.from_name}{" "}
                            <span className="text-slate-400 font-mono">&lt;{selectedEmail.from_email}&gt;</span>
                          </div>
                          <div>
                            <span className="font-bold text-slate-400">Date:</span>{" "}
                            {selectedEmail.received_at ? new Date(selectedEmail.received_at).toLocaleString() : ""}
                          </div>
                          <div>
                            <span className="font-bold text-slate-400">To Mailbox:</span>{" "}
                            {accounts.find(a => a.id === selectedEmail.mail_account_id)?.email}
                          </div>
                        </div>

                        {/* Body view toggle — only show if we have a body */}
                        {(emailDetail?.body_html || emailDetail?.body_text) && (
                          <div className="flex items-center space-x-1 border border-slate-800 rounded-lg p-0.5 self-start bg-slate-950/60">
                            <button
                              onClick={() => setEmailBodyView("html")}
                              disabled={!emailDetail?.body_html}
                              className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition cursor-pointer ${
                                emailBodyView === "html"
                                  ? "bg-indigo-600 text-white shadow-sm"
                                  : "text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
                              }`}
                            >
                              🎨 HTML
                            </button>
                            <button
                              onClick={() => setEmailBodyView("text")}
                              disabled={!emailDetail?.body_text}
                              className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition cursor-pointer ${
                                emailBodyView === "text"
                                  ? "bg-slate-700 text-white shadow-sm"
                                  : "text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
                              }`}
                            >
                              📄 Plain
                            </button>
                          </div>
                        )}

                        {/* HTML email rendered in sandboxed iframe */}
                        {emailDetail?.body_html && emailBodyView === "html" ? (
                          <div className="flex-1 rounded-xl overflow-hidden border border-slate-800/60" style={{ minHeight: "300px" }}>
                            <iframe
                              srcDoc={`<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><base target="_blank"><style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;line-height:1.6;color:#1a1a1a;background:#ffffff;margin:0;padding:16px;}a{color:#0066cc;}img{max-width:100%;height:auto;}*{box-sizing:border-box;}</style></head><body>${emailDetail.body_html.replace(/`/g, '\\`')}</body></html>`}
                              sandbox="allow-same-origin"
                              className="w-full h-full"
                              style={{ minHeight: "350px", border: "none", background: "white" }}
                              title="Email body"
                            />
                          </div>
                        ) : emailDetail?.body_text && (emailBodyView === "text" || !emailDetail?.body_html) ? (
                          <div className="flex-1 text-xs text-slate-300 leading-relaxed overflow-y-auto max-h-[45vh] bg-slate-950/30 border border-slate-900/60 p-4 rounded-xl whitespace-pre-wrap font-mono">
                            {emailDetail.body_text}
                          </div>
                        ) : (
                          <div className="flex-1 space-y-2">
                            <div className="text-xs text-slate-300 leading-relaxed overflow-y-auto max-h-[35vh] bg-slate-950/30 border border-slate-900/60 p-3 rounded-xl whitespace-pre-wrap font-sans">
                              {selectedEmail.snippet || "No preview available."}
                            </div>
                            <p className="text-[10px] text-slate-500 italic px-1">
                              Full email body will be available for newly synced emails.
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>
        )}

        {!dataLoading && activeTab === "mailboxes" && (
          <div className="space-y-6">
            
            {/* Accounts limits panel */}
            <div className="p-4 rounded-2xl glass border border-slate-900 flex items-center justify-between text-left">
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-white">Active Limit Tracking</h3>
                <p className="text-[10px] text-slate-400">
                  Plan boundaries are governed by your subscription plan.
                </p>
              </div>
              <div className="text-right">
                <span className="text-lg font-black text-white">
                  {accounts.filter(a => a.status !== "disconnected").length}
                </span>
                <span className="text-xs text-slate-500 font-bold">
                  {" "}/ {user.plan === "free" ? 3 : user.plan === "pro" ? 25 : 100}
                </span>
              </div>
            </div>

            {/* Notification Throttle Panel */}
            <div className="p-4 rounded-2xl glass border border-slate-900 text-left space-y-3">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <h3 className="text-xs font-bold text-white">🔔 Notification Limit</h3>
                  <p className="text-[10px] text-slate-400 leading-relaxed max-w-xs">
                    Max Telegram alerts per hour. Floor is automatically set to{" "}
                    <span className="text-indigo-400 font-bold">{notifLimitFloor}/hr</span>{" "}
                    based on your {accounts.filter(a => a.status !== "disconnected").length} accounts.
                  </p>
                </div>
                <span className="text-[10px] text-slate-500 bg-slate-900 border border-slate-800 px-2 py-1 rounded-lg shrink-0">
                  effective: <b className="text-indigo-400">{notifLimitEffective}/hr</b>
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min={1}
                  value={notifLimitInput}
                  onChange={(e) => setNotifLimitInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && saveNotifLimit()}
                  className="w-20 px-2.5 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 text-center"
                />
                <span className="text-[10px] text-slate-400">per hour</span>
                <button
                  onClick={saveNotifLimit}
                  disabled={notifLimitSaving}
                  className="px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-white text-[10px] font-semibold transition cursor-pointer disabled:opacity-50"
                >
                  {notifLimitSaving ? "Saving…" : "Save"}
                </button>
                {parseInt(notifLimitInput) < notifLimitFloor && (
                  <span className="text-[9px] text-amber-400">⚠ Floor enforced ({notifLimitFloor}/hr)</span>
                )}
              </div>
            </div>

            {/* Mass Controls Panel */}
            {(() => {
              const activeAccounts = accounts.filter(a => a.status !== "disconnected");
              if (activeAccounts.length === 0) return null;
              
              const allDashEnabled = activeAccounts.every(a => a.deliver_to_dashboard);
              const allAlertsEnabled = activeAccounts.every(a => a.notify_telegram);
              const allForwardEnabled = activeAccounts.every(a => a.forward_enabled);

              return (
                <div className="p-4 rounded-2xl glass border border-slate-900 text-left space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-0.5">
                      <h3 className="text-xs font-bold text-white">🎛️ Mass Controls</h3>
                      <p className="text-[10px] text-slate-400 leading-relaxed max-w-xs">
                        Apply preferences to all active mailboxes at once.
                      </p>
                    </div>
                  </div>
                  
                  <div className="pt-2 grid grid-cols-3 gap-1.5 text-[9px] font-semibold text-slate-400">
                    <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Enable/Disable Dash Delivery for all">
                      <input
                        type="checkbox"
                        checked={allDashEnabled}
                        onChange={(e) => handleMassTogglePreference("deliver_to_dashboard", e.target.checked)}
                        className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                      />
                      <span>📬 Dash</span>
                    </label>

                    <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Enable/Disable Telegram Alerts for all">
                      <input
                        type="checkbox"
                        checked={allAlertsEnabled}
                        onChange={(e) => handleMassTogglePreference("notify_telegram", e.target.checked)}
                        className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                      />
                      <span>🔔 Alerts</span>
                    </label>

                    <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Enable/Disable Email Forwarding for all">
                      <input
                        type="checkbox"
                        checked={allForwardEnabled}
                        onChange={(e) => handleMassTogglePreference("forward_enabled", e.target.checked)}
                        className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                      />
                      <span>📤 Forward</span>
                    </label>
                  </div>
                </div>
              );
            })()}

            {/* List of Connected Mailboxes */}
            <div>
              <h3 className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-3 px-1 text-left">
                Your Connected Mailboxes
              </h3>

              {accounts.filter(a => a.status !== "disconnected").length === 0 ? (
                <div className="p-8 text-center glass-card rounded-2xl border border-slate-900 text-slate-400 text-xs mb-6">
                  No active mailboxes connected. Add an account below to begin.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {accounts.filter(a => a.status !== "disconnected").map((acc) => {
                    return (
                      <div key={acc.id} className="p-4 rounded-2xl glass-card text-left border border-slate-900 flex flex-col justify-between min-h-[175px]">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className={`text-[8px] uppercase tracking-widest font-black px-1.5 py-0.5 rounded ${
                              acc.provider === "microsoft" ? "bg-blue-950/60 border border-blue-900/40 text-blue-400" :
                              acc.provider === "google" ? "bg-red-950/60 border border-red-900/40 text-red-400" :
                              "bg-slate-950 border border-slate-800 text-slate-400"
                            }`}>
                              {acc.provider}
                            </span>
                            <h4 className="text-xs font-bold text-white mt-2.5 truncate max-w-[200px]" title={acc.email}>
                              {acc.email}
                            </h4>
                          </div>

                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center ${
                            acc.status === "active" ? "bg-emerald-950/50 border border-emerald-900/30 text-emerald-400" :
                            acc.status === "syncing" ? "bg-indigo-950/50 border border-indigo-900/30 text-indigo-400" :
                            acc.status === "error" ? "bg-rose-950/50 border border-rose-900/30 text-rose-400 animate-pulse" :
                            "bg-slate-950 border border-slate-850 text-slate-400"
                          }`}>
                            {acc.status === "syncing" && <Loader2 className="h-3 w-3 animate-spin mr-1 text-indigo-400 shrink-0" />}
                            {acc.status === "active" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1.5 shrink-0" />}
                            {acc.status === "error" && <AlertCircle className="h-3 w-3 mr-1 text-rose-400 shrink-0" />}
                            {acc.status.toUpperCase()}
                          </span>
                        </div>

                        {/* Preferences Toggles */}
                        <div className="mt-3.5 pt-2 border-t border-slate-900/40 grid grid-cols-3 gap-1.5 text-[9px] font-semibold text-slate-400">
                          <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Show incoming emails on dashboard">
                            <input
                              type="checkbox"
                              checked={acc.deliver_to_dashboard}
                              onChange={(e) => handleTogglePreference(acc.id, "deliver_to_dashboard", e.target.checked)}
                              className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                            />
                            <span>📬 Dash</span>
                          </label>
                          <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Send alerts to your Telegram bot">
                            <input
                              type="checkbox"
                              checked={acc.notify_telegram}
                              onChange={(e) => handleTogglePreference(acc.id, "notify_telegram", e.target.checked)}
                              className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                            />
                            <span>🔔 Alerts</span>
                          </label>
                          <label className="flex items-center space-x-1.5 cursor-pointer select-none" title="Enable custom email forwarding rules">
                            <input
                              type="checkbox"
                              checked={acc.forward_enabled}
                              onChange={(e) => handleTogglePreference(acc.id, "forward_enabled", e.target.checked)}
                              className="accent-slate-500 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-3.5 w-3.5 shrink-0"
                            />
                            <span>📤 Forward</span>
                          </label>
                        </div>

                        <div className="flex items-end justify-between border-t border-slate-900/80 pt-3 mt-2.5">
                          <span className="text-[9px] text-slate-500">
                            Last Sync: {acc.last_sync ? new Date(acc.last_sync).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Never"}
                          </span>
                          
                          <button
                            onClick={() => handleDisconnect(acc.id)}
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/15 transition cursor-pointer"
                            title="Disconnect Mailbox"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Connect mailbox options */}
            <div className="border-t border-slate-900 pt-5">
              <h3 className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-3 px-1 text-left">
                Add Connection Provider
              </h3>
              
              <div className="grid grid-cols-1 xs:grid-cols-3 gap-3">
                <button
                  onClick={() => handleOAuthConnect("microsoft")}
                  className="py-3 px-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-blue-900/40 hover:bg-blue-950/10 text-slate-200 hover:text-blue-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm shadow-black/20"
                >
                  <div className="h-9 w-9 rounded-lg bg-blue-950/50 border border-blue-900/30 flex items-center justify-center text-blue-400 shadow-sm shrink-0">
                    <Sparkles className="h-4.5 w-4.5" />
                  </div>
                  <span>Microsoft Exchange</span>
                </button>

                <button
                  onClick={() => handleOAuthConnect("google")}
                  className="py-3 px-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-red-900/40 hover:bg-red-950/10 text-slate-200 hover:text-red-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm shadow-black/20"
                >
                  <div className="h-9 w-9 rounded-lg bg-red-950/50 border border-red-900/30 flex items-center justify-center text-red-400 shadow-sm shrink-0">
                    <Mail className="h-4.5 w-4.5" />
                  </div>
                  <span>Google Gmail</span>
                </button>

                <button
                  onClick={() => setShowImapDialog(true)}
                  className="py-3 px-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-900/40 hover:bg-indigo-950/10 text-slate-200 hover:text-indigo-300 text-xs font-semibold flex flex-col items-center justify-center space-y-2 transition cursor-pointer shadow-sm shadow-black/20"
                >
                  <div className="h-9 w-9 rounded-lg bg-indigo-950/50 border border-indigo-900/30 flex items-center justify-center text-indigo-400 shadow-sm shrink-0">
                    <Plus className="h-4.5 w-4.5" />
                  </div>
                  <span>Custom IMAP SSL</span>
                </button>
              </div>
            </div>

          </div>
        )}

        {!dataLoading && activeTab === "rules" && (
          <div className="space-y-6">
            
            {/* Header / Add Rule Button */}
            <div className="flex items-center justify-between text-left">
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-white">Email Forwarding Rules</h3>
                <p className="text-[10px] text-slate-400">
                  Configure custom rules to forward incoming emails to external addresses.
                </p>
              </div>
              <button
                onClick={() => setShowAddRuleForm(!showAddRuleForm)}
                className="py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow shadow-indigo-600/30"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{showAddRuleForm ? "Hide Form" : "New Rule"}</span>
              </button>
            </div>

            {/* Add Rule Form */}
            {showAddRuleForm && (
              <form onSubmit={handleAddRule} className="p-5 rounded-2xl glass border border-slate-900 text-left space-y-4">
                <h4 className="text-xs font-bold text-white mb-2">Create New Forwarding Rule</h4>

                {/* Scope Selection */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-400 block">Scope (Connected Account)</label>
                  <select
                    value={newRuleScope}
                    onChange={(e) => setNewRuleScope(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 cursor-pointer"
                  >
                    <option value="global">All Connected Mailboxes (Global)</option>
                    {accounts.filter(a => a.status !== "disconnected").map(acc => (
                      <option key={acc.id} value={acc.id}>Only: {acc.email}</option>
                    ))}
                  </select>
                </div>

                {/* Conditions Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 block">Subject Contains</label>
                    <input
                      type="text"
                      placeholder="e.g. Verification code, OTP"
                      value={newRuleSubject}
                      onChange={(e) => setNewRuleSubject(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 placeholder:text-slate-700"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 block">From Domain</label>
                    <input
                      type="text"
                      placeholder="e.g. netflix.com, google.com"
                      value={newRuleFromDomain}
                      onChange={(e) => setNewRuleFromDomain(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 placeholder:text-slate-700"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 block">From Email Address</label>
                    <input
                      type="email"
                      placeholder="e.g. info@netflix.com"
                      value={newRuleFromEmail}
                      onChange={(e) => setNewRuleFromEmail(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 placeholder:text-slate-700"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 block">Body Contains</label>
                    <input
                      type="text"
                      placeholder="e.g. single-use, security code"
                      value={newRuleBody}
                      onChange={(e) => setNewRuleBody(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 placeholder:text-slate-700"
                    />
                  </div>
                </div>

                {/* Target Address (Required) */}
                <div className="space-y-1.5 pt-1">
                  <label className="text-[10px] font-bold text-slate-400 block">Forward To (Target Email) *</label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. customer@outlook.com"
                    value={newRuleTarget}
                    onChange={(e) => setNewRuleTarget(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 placeholder:text-slate-700"
                  />
                </div>

                <div className="flex items-center justify-end space-x-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddRuleForm(false)}
                    className="py-1.5 px-4 rounded-xl border border-slate-800 hover:bg-slate-900 text-slate-400 text-xs font-semibold transition cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={ruleSubmitting}
                    className="py-1.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow shadow-indigo-600/30"
                  >
                    {ruleSubmitting && <Loader2 className="h-3 w-3 animate-spin mr-1 shrink-0" />}
                    <span>Create Rule</span>
                  </button>
                </div>
              </form>
            )}

            {/* List of Rules */}
            {rulesLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-6 w-6 text-indigo-500 animate-spin mb-2" />
                <p className="text-[10px] text-slate-400">Loading forwarding rules...</p>
              </div>
            ) : rules.length === 0 ? (
              <div className="p-8 text-center glass-card rounded-2xl border border-slate-900 text-slate-400 text-xs">
                No forwarding rules defined yet. Click "New Rule" above to get started.
              </div>
            ) : (
              <div className="space-y-4">
                {rules.map((rule) => {
                  const scopeAccount = accounts.find(a => a.id === rule.mail_account_id);
                  return (
                    <div key={rule.id} className="p-4 rounded-2xl glass-card text-left border border-slate-900 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="space-y-2.5 flex-1">
                        {/* Scope Indicator */}
                        <div className="flex items-center space-x-2">
                          <span className={`text-[8px] uppercase tracking-widest font-black px-1.5 py-0.5 rounded ${
                            rule.mail_account_id ? "bg-slate-900 border border-slate-805 text-slate-400" : "bg-indigo-950/60 border border-indigo-900/40 text-indigo-400"
                          }`}>
                            {rule.mail_account_id ? "Scoped Rule" : "Global Rule"}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {rule.mail_account_id ? `Applies to: ${scopeAccount?.email || 'Unknown Mailbox'}` : 'Applies to: All mailboxes'}
                          </span>
                        </div>

                        {/* Forward Destination */}
                        <div>
                          <p className="text-xs font-bold text-white flex items-center">
                            <span>Forward to:</span>
                            <span className="ml-1.5 text-indigo-400 underline decoration-indigo-800/40 select-all">{rule.forward_to_email}</span>
                          </p>
                        </div>

                        {/* Match Conditions List */}
                        <div className="flex flex-wrap gap-1.5">
                          {rule.condition_subject_contains && (
                            <span className="text-[9px] bg-slate-950 border border-slate-900 rounded px-1.5 py-0.5 text-slate-400">
                              Subject contains: <b>"{rule.condition_subject_contains}"</b>
                            </span>
                          )}
                          {rule.condition_from_domain && (
                            <span className="text-[9px] bg-slate-950 border border-slate-900 rounded px-1.5 py-0.5 text-slate-400">
                              From domain: <b>{rule.condition_from_domain}</b>
                            </span>
                          )}
                          {rule.condition_from_email && (
                            <span className="text-[9px] bg-slate-950 border border-slate-900 rounded px-1.5 py-0.5 text-slate-400">
                              From email: <b>{rule.condition_from_email}</b>
                            </span>
                          )}
                          {rule.condition_body_contains && (
                            <span className="text-[9px] bg-slate-950 border border-slate-900 rounded px-1.5 py-0.5 text-slate-400">
                              Body contains: <b>"{rule.condition_body_contains}"</b>
                            </span>
                          )}
                          {!rule.condition_subject_contains && !rule.condition_from_domain && !rule.condition_from_email && !rule.condition_body_contains && (
                            <span className="text-[9px] bg-emerald-950/40 border border-emerald-900/20 rounded px-1.5 py-0.5 text-emerald-400 italic">
                              Matches all incoming emails
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Rule Actions (Toggle Active / Delete) */}
                      <div className="flex items-center space-x-3.5 self-end md:self-center">
                        <label className="flex items-center space-x-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={rule.is_active}
                            onChange={(e) => handleToggleRuleActive(rule.id, e.target.checked)}
                            className="accent-indigo-600 rounded bg-slate-950 border-slate-800 focus:ring-0 cursor-pointer h-4 w-4 shrink-0"
                          />
                          <span className="text-[10px] font-bold text-slate-400">Active</span>
                        </label>
                        
                        <button
                          onClick={() => handleDeleteRule(rule.id)}
                          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/15 transition cursor-pointer"
                          title="Delete Rule"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

      </main>

      {/* Custom IMAP Dialog Overlay */}
      {showImapDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="max-w-md w-full glass-card border border-slate-800 rounded-2xl p-6 shadow-2xl text-left relative">
            <h3 className="text-sm font-bold text-white flex items-center space-x-1.5 mb-3">
              <Mail className="h-4 w-4 text-indigo-400" />
              <span>Connect Custom IMAP Mailbox</span>
            </h3>

            {/* Security warning — prominent */}
            <div className="mb-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-300 leading-relaxed space-y-1">
              <div className="flex items-center space-x-1.5 font-bold text-amber-400">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                <span>App-Specific Password Required</span>
              </div>
              <p>
                Never enter your main account password here. Use an <b>app password</b> generated separately:
              </p>
              <ul className="list-disc ml-4 space-y-0.5">
                <li><b>Gmail:</b> Account → Security → 2-Step Verification → App Passwords</li>
                <li><b>Outlook:</b> account.microsoft.com → Security → Advanced Security Options</li>
                <li><b>Yahoo:</b> Account Security → Generate app password</li>
              </ul>
            </div>

            {imapError && (
              <div className="mb-4 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[10px] text-rose-400 flex items-start space-x-1.5">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span>{imapError}</span>
              </div>
            )}

            <form onSubmit={handleImapConnect} className="space-y-3.5">
              <div>
                <label className="block text-[9px] uppercase font-bold text-slate-400 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={imapEmail}
                  onChange={(e) => setImapEmail(e.target.value)}
                  placeholder="e.g. john@yahoo.com"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[9px] uppercase font-bold text-slate-400 mb-1">App Password</label>
                <input
                  type="password"
                  required
                  value={imapPassword}
                  onChange={(e) => setImapPassword(e.target.value)}
                  placeholder="e.g. xxxx-xxxx-xxxx-xxxx"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-[9px] uppercase font-bold text-slate-400 mb-1">IMAP Host</label>
                  <input
                    type="text"
                    required
                    value={imapHost}
                    onChange={(e) => setImapHost(e.target.value)}
                    placeholder="e.g. imap.mail.yahoo.com"
                    className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-[9px] uppercase font-bold text-slate-400 mb-1">SSL Port</label>
                  <input
                    type="text"
                    required
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    placeholder="993"
                    className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-slate-900/80 mt-4">
                <button
                  type="button"
                  onClick={() => { setShowImapDialog(false); setImapError(null); }}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-850 hover:border-slate-800 text-slate-400 text-xs font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={imapConnecting}
                  className="px-4 py-1.5 rounded-lg bg-indigo-650 hover:bg-indigo-600 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
                >
                  {imapConnecting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <span>Link Mailbox</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
