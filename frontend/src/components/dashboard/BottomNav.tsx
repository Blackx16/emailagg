"use client";

import React from "react";
import { Inbox, Activity, SlidersHorizontal } from "lucide-react";

export type TabType = "inbox" | "mailboxes" | "rules";

interface BottomNavProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  unreadCount?: number;
}

const TABS: { id: TabType; label: string; icon: React.ElementType }[] = [
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "mailboxes", label: "Mailboxes", icon: Activity },
  { id: "rules", label: "Rules", icon: SlidersHorizontal },
];

export default function BottomNav({ activeTab, setActiveTab, unreadCount }: BottomNavProps) {
  const triggerHaptic = () => {
    if (typeof window !== "undefined") {
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.HapticFeedback) {
        try {
          if (typeof tg.HapticFeedback.selectionChanged === "function") {
            tg.HapticFeedback.selectionChanged();
          } else if (typeof tg.HapticFeedback.impactOccurred === "function") {
            tg.HapticFeedback.impactOccurred("light");
          }
        } catch (e) {
          console.warn("Haptic feedback call failed:", e);
        }
      }
    }
  };

  const handleTabClick = (tabId: TabType) => {
    if (activeTab !== tabId) {
      triggerHaptic();
      setActiveTab(tabId);
    }
  };

  return (
    <div
      className="fixed inset-x-4 max-w-md mx-auto z-40 transition-all duration-300 pointer-events-auto"
      style={{
        bottom: "calc(1rem + env(safe-area-inset-bottom, 0px))",
      }}
    >
      <nav
        className="backdrop-blur-xl bg-[var(--glass-bg)] border border-[var(--border)] rounded-full shadow-2xl p-1.5 flex items-center justify-between relative select-none"
        aria-label="Bottom Navigation"
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => handleTabClick(tab.id)}
              className={`relative flex-1 flex items-center justify-center space-x-2 py-2.5 px-3 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer z-10 ${
                isActive
                  ? "text-[var(--text-primary)]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {/* Active Tab Pill Background Indicator */}
              {isActive && (
                <div className="absolute inset-0 bg-[var(--bg-elevated)] border border-[var(--border-strong)] rounded-full shadow-sm -z-10 transition-all duration-200" />
              )}

              <Icon className={`h-4 w-4 transition-colors ${isActive ? "text-indigo-500" : ""}`} />
              <span className="tracking-tight">{tab.label}</span>

              {/* Optional Unread Badge */}
              {tab.id === "inbox" && unreadCount !== undefined && unreadCount > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[9px] font-bold bg-indigo-500 text-white rounded-full leading-none">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
