import React, { useRef, useEffect } from "react";
import { Search, Inbox, Clock, ChevronLeft, ChevronRight, Plus, ChevronDown, X } from "lucide-react";
import { Account, EmailItem } from "../../types/dashboard";
import EmailDetail from "./EmailDetail";

function FilterDropdown({ value, options, onChange, label, className = "" }: any) {
  const [isOpen, setIsOpen] = React.useState(false);
  const selectedLabel = options.find((o: any) => o.value === value)?.label || label;

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] rounded-lg pl-3 pr-8 py-2.5 text-xs font-medium text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 cursor-pointer transition-colors text-left truncate"
      >
        {selectedLabel}
        <span className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <ChevronDown className={`w-3.5 h-3.5 text-[var(--text-tertiary)] transition-transform ${isOpen ? "rotate-180" : ""}`} />
        </span>
      </button>

      {/* Mobile: bottom sheet. Desktop: inline dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/40 md:bg-transparent"
            onClick={() => setIsOpen(false)}
          />

          {/* Desktop dropdown */}
          <div className="hidden md:block absolute z-50 mt-1 w-full bg-[var(--bg-elevated)] border border-[var(--border-strong)] rounded-lg shadow-2xl overflow-hidden min-w-max">
            {options.map((opt: any) => (
              <button
                key={opt.value}
                type="button"
                className={`block w-full text-left px-3 py-2.5 text-xs transition-colors ${
                  value === opt.value
                    ? "bg-[var(--accent-muted)] text-[var(--text-primary)] font-semibold"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                }`}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Mobile bottom sheet */}
          <div className="md:hidden fixed inset-x-0 bottom-0 z-50 animate-slide-up">
            <div className="bg-[var(--bg-elevated)] border-t border-[var(--border-strong)] rounded-t-2xl shadow-2xl px-2 pb-8 pt-3 max-h-[60vh] overflow-y-auto">
              {/* Handle bar */}
              <div className="flex justify-center mb-3">
                <div className="w-10 h-1 rounded-full bg-[var(--border-strong)]" />
              </div>
              {/* Header */}
              <div className="flex items-center justify-between px-3 mb-2">
                <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-tertiary)] cursor-pointer transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              {/* Options */}
              {options.map((opt: any) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`block w-full text-left px-4 py-3.5 text-sm rounded-lg mb-0.5 transition-colors ${
                    value === opt.value
                      ? "bg-[var(--accent-muted)] text-[var(--text-primary)] font-semibold"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                  }`}
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface InboxTabProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  handleSearchSubmit: (e: React.FormEvent) => void;
  handleClearSearch: () => void;
  activeSearch: string;
  statusFilter: string;
  setStatusFilter: (filter: string) => void;
  providerFilter: string;
  setProviderFilter: (filter: string) => void;
  mailboxFilter: string;
  setMailboxFilter: (filter: string) => void;
  accounts: Account[];
  emails: EmailItem[];
  selectedEmail: EmailItem | null;
  setSelectedEmail: (email: EmailItem | null) => void;
  handleSelectEmail: (email: EmailItem) => void;
  page: number;
  handlePageChange: (page: number) => void;
  limit: number;
  totalPages: number;
  totalEmails: number;
  emailDetailLoading: boolean;
  emailDetail: any;
  emailBodyView: "html" | "text";
  setEmailBodyView: (view: "html" | "text") => void;
  setActiveTab: (tab: "inbox" | "mailboxes" | "rules") => void;
}

export default function InboxTab({
  searchQuery, setSearchQuery, handleSearchSubmit, handleClearSearch, activeSearch,
  statusFilter, setStatusFilter, providerFilter, setProviderFilter, mailboxFilter, setMailboxFilter,
  accounts, emails, selectedEmail, setSelectedEmail, handleSelectEmail,
  page, handlePageChange, limit, totalPages, totalEmails,
  emailDetailLoading, emailDetail, emailBodyView, setEmailBodyView,
  setActiveTab
}: InboxTabProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search subject or sender..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 shadow-inner transition-shadow"
          />
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-[var(--text-tertiary)]" />
          {activeSearch && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-3.5 top-3 text-[10px] uppercase font-bold tracking-wider text-[var(--text-tertiary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/50 rounded transition cursor-pointer"
            >
              Clear
            </button>
          )}
        </form>

        <div className="flex items-center space-x-2 pb-1 md:pb-0">
          <FilterDropdown
            value={statusFilter}
            onChange={setStatusFilter}
            label="All Status"
            className="min-w-[120px]"
            options={[
              { value: "all", label: "All Status" },
              { value: "unread", label: "Unread Only" },
              { value: "read", label: "Read Only" },
            ]}
          />
          <FilterDropdown
            value={providerFilter}
            onChange={setProviderFilter}
            label="All Providers"
            className="min-w-[125px]"
            options={[
              { value: "all", label: "All Providers" },
              { value: "microsoft", label: "Microsoft" },
              { value: "google", label: "Google" },
              { value: "imap", label: "IMAP" },
            ]}
          />
          <FilterDropdown
            value={mailboxFilter}
            onChange={setMailboxFilter}
            label="All Mailboxes"
            className="min-w-[140px] max-w-[160px]"
            options={[
              { value: "all", label: "All Mailboxes" },
              ...accounts.filter(a => a.status !== "disconnected").map(acc => ({
                value: acc.id,
                label: acc.email
              }))
            ]}
          />
        </div>
      </div>

      {emails.length === 0 ? (
        <div className="text-center py-16 px-6 glass-card rounded-xl border border-[var(--border)]">
          <div className="h-12 w-12 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4">
            <Inbox className="h-6 w-6 text-[var(--text-tertiary)]" />
          </div>
          {activeSearch || statusFilter !== "all" || providerFilter !== "all" || mailboxFilter !== "all" ? (
            <>
              <h3 className="text-sm font-bold tracking-tight text-[var(--text-primary)] mb-1">No matching emails</h3>
              <p className="text-xs text-[var(--text-secondary)] font-medium max-w-xs mx-auto mb-5 leading-relaxed">
                No emails match your active search term or filter selection.
              </p>
              <button
                onClick={() => {
                  setSearchQuery("");
                  handleClearSearch();
                  setStatusFilter("all");
                  setProviderFilter("all");
                  setMailboxFilter("all");
                }}
                className="inline-flex items-center space-x-1.5 py-1.5 px-3.5 bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text-primary)] text-xs font-semibold rounded-lg transition cursor-pointer"
              >
                Clear Filters
              </button>
            </>
          ) : (
            <>
              <h3 className="text-sm font-bold tracking-tight text-[var(--text-primary)] mb-1">No emails yet</h3>
              <p className="text-xs text-[var(--text-secondary)] font-medium max-w-xs mx-auto mb-5 leading-relaxed">
                Aggregated emails will appear here as soon as they arrive in your connected inboxes.
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
          <div className={`space-y-4 md:col-span-3 ${selectedEmail ? "hidden md:block" : "block"}`}>
            <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2 px-1">
              Inbox
            </h2>
            
            <div className="space-y-2 overflow-y-auto max-h-[70vh] pr-1">
              {emails.map((email) => {
                const dateObj = email.received_at ? new Date(email.received_at) : null;
                const formattedTime = dateObj ? dateObj.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
                const accountEmail = accounts.find(a => a.id === email.mail_account_id)?.email || "";
                
                return (
                  <div
                    key={email.id}
                    onClick={() => handleSelectEmail(email)}
                    className={`p-4 rounded-xl cursor-pointer text-left glass glass-interactive border transition-all ${
                      selectedEmail?.id === email.id
                        ? "bg-[var(--bg-elevated)] border-indigo-500/60 shadow-lg"
                        : "border-[var(--border)]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold tracking-tight text-[var(--text-primary)] truncate max-w-[150px]">
                        {email.from_name || email.from_email || "Unknown Sender"}
                      </span>
                      <span className="text-[9px] text-[var(--text-tertiary)] flex items-center shrink-0">
                        <Clock className="h-3 w-3 mr-0.5 shrink-0" />
                        {formattedTime}
                      </span>
                    </div>
                    
                    <h4 className="text-xs font-medium tracking-tight text-[var(--text-primary)] truncate mb-1">
                      {email.subject || "(No Subject)"}
                    </h4>
                    
                    <p className="text-[10px] text-[var(--text-secondary)] line-clamp-2 leading-relaxed mb-2">
                      {email.snippet || "No preview snippet available."}
                    </p>

                    <div className="flex items-center justify-between border-t border-[var(--border)] pt-2 text-[8px] tracking-widest uppercase font-bold text-[var(--text-tertiary)]">
                      <span>Inbox: {accountEmail}</span>
                      {email.has_attachment && (
                        <span className="bg-[var(--bg-surface)] border border-[var(--border)] px-1 rounded text-cyan-500">
                          📎 Attachment
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-[var(--border)] pt-4 mt-4 text-xs text-[var(--text-secondary)] px-1">
                <span>
                  Showing {(page - 1) * limit + 1} - {Math.min(page * limit, totalEmails)} of {totalEmails}
                </span>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                    className="p-1.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition cursor-pointer"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="px-3 font-semibold text-[var(--text-primary)]">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page === totalPages}
                    className="p-1.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition cursor-pointer"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          <EmailDetail
            selectedEmail={selectedEmail}
            setSelectedEmail={setSelectedEmail}
            emailDetailLoading={emailDetailLoading}
            emailDetail={emailDetail}
            emailBodyView={emailBodyView}
            setEmailBodyView={setEmailBodyView}
            accounts={accounts}
          />
        </div>
      )}

      {/* Bottom sheet slide-up animation */}
      <style jsx>{`
        @keyframes slide-up {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}</style>
    </div>
  );
}
