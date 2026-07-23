"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Account, EmailItem } from "../types/dashboard";

import DevLogin from "../components/dashboard/DevLogin";
import InboxTab from "../components/dashboard/InboxTab";
import MailboxesTab from "../components/dashboard/MailboxesTab";
import RulesTab from "../components/dashboard/RulesTab";
import BottomNav, { TabType } from "../components/dashboard/BottomNav";

const TABS: TabType[] = ["inbox", "mailboxes", "rules"];

export default function Dashboard() {
  const { user, token, loading: authLoading, error, isTelegramWebApp, loginManual, logout } = useAuth();

  const [activeTab, setActiveTab] = useState<TabType>("inbox");
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

  // Disable vertical swipes on mount to prevent Telegram Mini App closure
  useEffect(() => {
    if (typeof window !== "undefined") {
      const tg = (window as any).Telegram?.WebApp;
      if (tg && typeof tg.disableVerticalSwipes === "function") {
        try {
          tg.disableVerticalSwipes();
        } catch (e) {
          console.warn("Failed to call disableVerticalSwipes:", e);
        }
      }
    }
  }, []);

  // Swipe Gesture Handling
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const triggerHaptic = () => {
    if (typeof window !== "undefined") {
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.HapticFeedback) {
        try {
          if (typeof tg.HapticFeedback.selectionChanged === "function") {
            tg.HapticFeedback.selectionChanged();
          }
        } catch (e) {}
      }
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      touchStartRef.current = {
        x: e.touches[0].clientX,
        y: e.touches[0].clientY,
      };
    }
  };

  const handleTouchCancel = () => {
    touchStartRef.current = null;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current || e.changedTouches.length !== 1) return;

    const startX = touchStartRef.current.x;
    const startY = touchStartRef.current.y;
    const endX = e.changedTouches[0].clientX;
    const endY = e.changedTouches[0].clientY;
    touchStartRef.current = null;

    const deltaX = endX - startX;
    const deltaY = endY - startY;

    // Require horizontal swipe to clearly dominate vertical movement (ratio > 1.5) and minimum swipe distance > 60px
    if (Math.abs(deltaX) > Math.abs(deltaY) * 1.5 && Math.abs(deltaX) > 60) {
      const currentIndex = TABS.indexOf(activeTab);
      if (deltaX < 0 && currentIndex < TABS.length - 1) {
        // Swipe Left -> next tab
        const nextTab = TABS[currentIndex + 1];
        setActiveTab(nextTab);
        triggerHaptic();
      } else if (deltaX > 0 && currentIndex > 0) {
        // Swipe Right -> previous tab
        const prevTab = TABS[currentIndex - 1];
        setActiveTab(prevTab);
        triggerHaptic();
      }
    }
  };

  const fetchData = useCallback(async (isRefresh = false) => {
    if (!token) return;
    if (isRefresh) setRefreshing(true);

    try {
      setRulesLoading(true);

      const searchParams = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      if (activeSearch) searchParams.append("q", activeSearch);
      if (statusFilter !== "all") searchParams.append("status", statusFilter);
      if (providerFilter !== "all") searchParams.append("provider", providerFilter);
      if (mailboxFilter !== "all") searchParams.append("account_id", mailboxFilter);

      const [accountsRes, userRes, emailsRes, rulesRes] = await Promise.all([
        fetch("/api/v1/accounts", { headers: { "Authorization": `Bearer ${token}` } }),
        fetch("/api/v1/auth/me", { headers: { "Authorization": `Bearer ${token}` } }),
        fetch(`/api/v1/emails?${searchParams.toString()}`, { headers: { "Authorization": `Bearer ${token}` } }),
        fetch("/api/v1/rules", { headers: { "Authorization": `Bearer ${token}` } })
      ]);

      if (accountsRes.ok) {
        const accs = await accountsRes.json();
        setAccounts(accs);
      }

      if (userRes.ok) {
        const userData = await userRes.json();
        setNotifLimitEffective(userData.notification_limit_effective || 0);
        setNotifLimitFloor(userData.notification_limit_floor || 0);
        setNotifLimitInput((userData.notification_limit_effective || 0).toString());
      }

      if (emailsRes.ok) {
        const data = await emailsRes.json();
        setEmails(data.emails || []);
        setTotalEmails(data.total || 0);
        setTotalPages(data.total_pages || 1);
      }

      if (rulesRes.ok) {
        setRules(await rulesRes.json());
      }
      setRulesLoading(false);

    } catch (err) {
      console.error("Failed to fetch data:", err);
      setRulesLoading(false);
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
      const res = await fetch(`/api/v1/emails/${email.id}`, {
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
      const res = await fetch(`/api/v1/auth/oauth/${provider}/login`, {
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
      const res = await fetch(`/api/v1/accounts/${accountId}`, {
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
      
      const res = await fetch(`/api/v1/accounts/${accountId}`, {
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
        await fetch(`/api/v1/accounts/${accountId}`, {
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
      const res = await fetch("/api/v1/auth/me/limit", {
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
      <div className="flex-1 flex flex-col items-center justify-center min-h-screen" style={{ backgroundColor: 'var(--bg)' }}>
        <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-4" />
        <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-wide">EmailAgg</h1>
        <p className="text-sm text-[var(--text-tertiary)]">Initializing connection...</p>
      </div>
    );
  }

  // Check if we're in the Telegram environment even if isTelegramWebApp is false
  const isInsideTelegram = typeof window !== 'undefined' && 
                           (window as any).Telegram && 
                           (window as any).Telegram.WebApp && 
                           (window as any).Telegram.WebApp.platform && 
                           (window as any).Telegram.WebApp.platform !== "unknown";

  if (!token && (isTelegramWebApp || isInsideTelegram)) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center min-h-screen" style={{ backgroundColor: 'var(--bg)' }}>
        <h2 className="text-lg font-bold text-rose-400 mb-2">Session Expired</h2>
        <p className="text-sm text-[var(--text-secondary)] max-w-sm mb-6">
          Your session has been logged out or could not be verified. {error}
        </p>
        <button
          onClick={() => {
            window.location.reload();
          }}
          className="flex items-center space-x-2 py-2.5 px-6 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg focus:outline-none transition duration-200 shadow-md cursor-pointer"
        >
          <span>Log back in seamlessly</span>
        </button>
      </div>
    );
  }

  if (!token && !isTelegramWebApp) {
    return <DevLogin error={error} loginManual={loginManual} />;
  }

  const activeTabIndex = TABS.indexOf(activeTab);

  return (
    <div className="flex-1 flex flex-col min-h-screen relative" style={{ backgroundColor: 'var(--bg)' }}>
      {/* Top Header removed per Requirement R1 */}

      <main className="flex-1 p-4 md:p-6 w-full max-w-[1400px] mx-auto pb-28 md:pb-32">
        {dataLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin mb-4" />
            <p className="text-xs font-medium text-[var(--text-secondary)]">
              Synchronizing data...
            </p>
          </div>
        ) : (
          <div
            className="relative w-full"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            onTouchCancel={handleTouchCancel}
            style={{ overflow: "clip" }}
          >
            {/* Tab slide container — each tab is absolute when inactive so it doesn't
                contribute to document height, eliminating the Mailboxes excessive-scroll bug.
                The active tab is relative (in flow) so page height = active tab content only. */}
            {/* Tab 0: Unified Inbox */}
            <div
              className={`w-full transition-transform duration-300 ease-out px-0.5 ${activeTabIndex === 0 ? "relative" : "absolute top-0 left-0 pointer-events-none"}`}
              style={{ transform: `translateX(${(0 - activeTabIndex) * 100}%)` }}
              aria-hidden={activeTabIndex !== 0}
            >
              <InboxTab
                onRefresh={() => fetchData(true)}
                isRefreshing={refreshing}
                refreshing={refreshing}
                fetchData={fetchData}
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
            </div>

            {/* Tab 1: Mailboxes & Settings */}
            <div
              className={`w-full transition-transform duration-300 ease-out px-0.5 ${activeTabIndex === 1 ? "relative" : "absolute top-0 left-0 pointer-events-none"}`}
              style={{ transform: `translateX(${(1 - activeTabIndex) * 100}%)` }}
              aria-hidden={activeTabIndex !== 1}
            >
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
                logout={logout}
              />
            </div>

            {/* Tab 2: Forwarding Rules */}
            <div
              className={`w-full transition-transform duration-300 ease-out px-0.5 ${activeTabIndex === 2 ? "relative" : "absolute top-0 left-0 pointer-events-none"}`}
              style={{ transform: `translateX(${(2 - activeTabIndex) * 100}%)` }}
              aria-hidden={activeTabIndex !== 2}
            >
              <RulesTab
                token={token}
                accounts={accounts}
                rules={rules}
                rulesLoading={rulesLoading}
                fetchData={fetchData}
              />
            </div>
          </div>
        )}
      </main>

      {/* Floating Translucent Bottom Navigation Bar per Requirement R2 */}
      <BottomNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
    </div>
  );
}
