"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Inbox, Activity, SlidersHorizontal, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Account, EmailItem } from "../types/dashboard";

import Header from "../components/dashboard/Header";
import DevLogin from "../components/dashboard/DevLogin";
import InboxTab from "../components/dashboard/InboxTab";
import MailboxesTab from "../components/dashboard/MailboxesTab";
import RulesTab from "../components/dashboard/RulesTab";

export default function Dashboard() {
  const { user, token, loading: authLoading, error, isTelegramWebApp, tgWebApp, loginManual, logout, retryLogin } = useAuth();

  const [activeTab, setActiveTab] = useState<"inbox" | "mailboxes" | "rules">("inbox");
  const [dataLoading, setDataLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // States
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [rulesLoading, setRulesLoading] = useState(false);

  const [notifLimitEffective, setNotifLimitEffective] = useState<number>(0);
  const [notifLimitFloor, setNotifLimitFloor] = useState<number>(0);
  const [notifLimitInput, setNotifLimitInput] = useState("");
  const [notifLimitSaving, setNotifLimitSaving] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [providerFilter, setProviderFilter] = useState("all");
  const [mailboxFilter, setMailboxFilter] = useState("all");

  const [page, setPage] = useState(1);
  const [totalEmails, setTotalEmails] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 20;

  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(null);
  const [emailDetailLoading, setEmailDetailLoading] = useState(false);
  const [emailDetail, setEmailDetail] = useState<any>(null);
  const [emailBodyView, setEmailBodyView] = useState<"html" | "text">("html");

  const fetchData = useCallback(async (isRefresh = false) => {
    if (!token) return;
    if (isRefresh) setRefreshing(true);

    try {
      // 1. Fetch Accounts
      const accountsRes = await fetch("/api/mail/accounts", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (accountsRes.ok) {
        const accs = await accountsRes.json();
        setAccounts(accs);
      }

      // 2. Fetch User Settings
      const userRes = await fetch("/api/auth/me", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (userRes.ok) {
        const userData = await userRes.json();
        setNotifLimitEffective(userData.notification_limit_effective || 0);
        setNotifLimitFloor(userData.notification_limit_floor || 0);
        setNotifLimitInput((userData.notification_limit_effective || 0).toString());
      }

      // 3. Fetch Emails with pagination/filters
      const searchParams = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      if (activeSearch) searchParams.append("q", activeSearch);
      if (statusFilter !== "all") searchParams.append("status", statusFilter);
      if (providerFilter !== "all") searchParams.append("provider", providerFilter);
      if (mailboxFilter !== "all") searchParams.append("account_id", mailboxFilter);

      const emailsRes = await fetch(`/api/mail/emails?${searchParams.toString()}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (emailsRes.ok) {
        const data = await emailsRes.json();
        setEmails(data.items || []);
        setTotalEmails(data.total || 0);
        setTotalPages(data.pages || 1);
      }

      // 4. Fetch Rules
      setRulesLoading(true);
      const rulesRes = await fetch("/api/rules", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (rulesRes.ok) {
        setRules(await rulesRes.json());
      }
      setRulesLoading(false);

    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setDataLoading(false);
      setRefreshing(false);
    }
  }, [token, page, limit, activeSearch, statusFilter, providerFilter, mailboxFilter]);

  useEffect(() => {
    if (token) {
      fetchData();
      
      const interval = setInterval(() => {
        if (!document.hidden) {
          fetchData(true);
        }
      }, 30000); // 30s auto-refresh
      
      return () => clearInterval(interval);
    }
  }, [token, fetchData]);

  const handleSelectEmail = async (email: EmailItem) => {
    setSelectedEmail(email);
    setEmailDetail(null);
    setEmailBodyView("html");
    
    if (!token) return;
    
    setEmailDetailLoading(true);
    try {
      const res = await fetch(`/api/mail/emails/${email.id}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const detail = await res.json();
        setEmailDetail(detail);
        if (!detail.body_html && detail.body_text) {
          setEmailBodyView("text");
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setEmailDetailLoading(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchQuery);
    setPage(1); // Reset page on new search
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setActiveSearch("");
    setPage(1);
  };

  const handleOAuthConnect = async (provider: "microsoft" | "google") => {
    if (!token) return;
    try {
      const res = await fetch(`/api/auth/oauth/${provider}/login`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error(`Failed to initiate ${provider} flow`);
      const data = await res.json();
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      console.error(err);
      alert(`Error starting ${provider} connection.`);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    if (!token) return;
    if (!confirm("Are you sure you want to disconnect this mailbox?")) return;
    
    try {
      const res = await fetch(`/api/mail/accounts/${accountId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete account");
      fetchData(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePreference = async (accountId: string, field: string, value: boolean) => {
    if (!token) return;
    try {
      setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, [field]: value } : a));
      
      const payload: any = {};
      payload[field] = value;
      
      const res = await fetch(`/api/mail/accounts/${accountId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, [field]: !value } : a));
      }
    } catch (err) {
      console.error(err);
      setAccounts(prev => prev.map(a => a.id === accountId ? { ...a, [field]: !value } : a));
    }
  };

  const handleMassTogglePreference = async (field: string, value: boolean) => {
    if (!token) return;
    try {
      const activeIds = accounts.filter(a => a.status !== "disconnected").map(a => a.id);
      
      setAccounts(prev => prev.map(a => {
        if (a.status !== "disconnected") {
          return { ...a, [field]: value };
        }
        return a;
      }));
      
      for (const accountId of activeIds) {
        const payload: any = {};
        payload[field] = value;
        await fetch(`/api/mail/accounts/${accountId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
      }
    } catch (err) {
      console.error(err);
      fetchData(true);
    }
  };

  const saveNotifLimit = async () => {
    if (!token) return;
    
    let parsedLimit = parseInt(notifLimitInput);
    if (isNaN(parsedLimit) || parsedLimit < notifLimitFloor) {
      parsedLimit = notifLimitFloor;
      setNotifLimitInput(parsedLimit.toString());
    }

    setNotifLimitSaving(true);
    try {
      const res = await fetch("/api/auth/me/limit", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ notification_limit: parsedLimit })
      });

      if (!res.ok) throw new Error("Failed to save limit");
      const data = await res.json();
      setNotifLimitEffective(data.notification_limit_effective);
    } catch (err) {
      console.error(err);
    } finally {
      setNotifLimitSaving(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#090a0f]">
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-4" />
        <h1 className="text-xl font-bold text-white tracking-wide">EmailAgg</h1>
        <p className="text-sm text-slate-500">Initializing connection...</p>
      </div>
    );
  }

  // Check if we're in the Telegram environment even if isTelegramWebApp is false (e.g. initData missing)
  const isInsideTelegram = typeof window !== 'undefined' && 
                           (window as any).Telegram && 
                           (window as any).Telegram.WebApp && 
                           (window as any).Telegram.WebApp.platform && 
                           (window as any).Telegram.WebApp.platform !== "unknown";

  if (!token && (isTelegramWebApp || isInsideTelegram)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-[#090a0f] p-6 text-center">
        <h2 className="text-lg font-bold text-rose-400 mb-2">Session Expired</h2>
        <p className="text-sm text-slate-400 max-w-sm mb-6">
          Your session has been logged out or could not be verified. {error}
        </p>
        <button
          onClick={() => {
            window.location.reload();
          }}
          className="flex items-center space-x-2 py-2.5 px-6 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg focus:outline-none transition duration-200 shadow-md"
        >
          <span>Log back in seamlessly</span>
        </button>
      </div>
    );
  }

  if (!token && !isTelegramWebApp) {
    return <DevLogin error={error} loginManual={loginManual} />;
  }

  return (
    <div className="flex-1 flex flex-col bg-[#090a0f] min-h-screen">
      <Header user={user} refreshing={refreshing} fetchData={fetchData} logout={logout} />

      <main className="flex-1 p-4 md:p-6 w-full max-w-[1400px] mx-auto">
        <div className="flex items-center space-x-1.5 mb-6 glass p-1.5 rounded-xl border border-slate-700/50 inline-flex shadow-sm">
          <button
            onClick={() => setActiveTab("inbox")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
              activeTab === "inbox" 
                ? "bg-slate-800 text-white shadow-sm" 
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <Inbox className="h-4 w-4" />
            <span>Unified Inbox</span>
          </button>
          <button
            onClick={() => setActiveTab("mailboxes")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
              activeTab === "mailboxes" 
                ? "bg-slate-800 text-white shadow-sm" 
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <Activity className="h-4 w-4" />
            <span>Mailboxes & Settings</span>
          </button>
          <button
            onClick={() => setActiveTab("rules")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
              activeTab === "rules" 
                ? "bg-slate-800 text-white shadow-sm" 
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>Forwarding Rules</span>
          </button>
        </div>

        {dataLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-4" />
            <p className="text-xs font-medium text-slate-400 uppercase tracking-widest">
              Synchronizing data...
            </p>
          </div>
        ) : (
          <>
            {activeTab === "inbox" && (
              <InboxTab
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                handleSearchSubmit={handleSearchSubmit}
                handleClearSearch={handleClearSearch}
                activeSearch={activeSearch}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                providerFilter={providerFilter}
                setProviderFilter={setProviderFilter}
                mailboxFilter={mailboxFilter}
                setMailboxFilter={setMailboxFilter}
                accounts={accounts}
                emails={emails}
                selectedEmail={selectedEmail}
                setSelectedEmail={setSelectedEmail}
                handleSelectEmail={handleSelectEmail}
                page={page}
                handlePageChange={handlePageChange}
                limit={limit}
                totalPages={totalPages}
                totalEmails={totalEmails}
                emailDetailLoading={emailDetailLoading}
                emailDetail={emailDetail}
                emailBodyView={emailBodyView}
                setEmailBodyView={setEmailBodyView}
                setActiveTab={setActiveTab}
              />
            )}
            {activeTab === "mailboxes" && (
              <MailboxesTab
                user={user}
                token={token}
                accounts={accounts}
                notifLimitEffective={notifLimitEffective}
                notifLimitFloor={notifLimitFloor}
                notifLimitInput={notifLimitInput}
                setNotifLimitInput={setNotifLimitInput}
                notifLimitSaving={notifLimitSaving}
                saveNotifLimit={saveNotifLimit}
                handleMassTogglePreference={handleMassTogglePreference}
                handleTogglePreference={handleTogglePreference}
                handleDisconnect={handleDisconnect}
                handleOAuthConnect={handleOAuthConnect}
                fetchData={fetchData}
              />
            )}
            {activeTab === "rules" && (
              <RulesTab
                token={token}
                accounts={accounts}
                rules={rules}
                rulesLoading={rulesLoading}
                fetchData={fetchData}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
