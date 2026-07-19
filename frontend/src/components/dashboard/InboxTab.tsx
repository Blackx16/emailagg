import React from "react";
import { Search, Inbox, Clock, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { Account, EmailItem } from "../../types/dashboard";
import EmailDetail from "./EmailDetail";

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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/50 pb-4">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search subject or sender..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 shadow-inner"
          />
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
          {activeSearch && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-3.5 top-3 text-[10px] uppercase font-bold tracking-wider text-slate-400 hover:text-white transition cursor-pointer"
            >
              Clear
            </button>
          )}
        </form>

        <div className="flex items-center space-x-2 overflow-x-auto pb-1 md:pb-0 scrollbar-hide">
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="appearance-none bg-slate-800 border border-slate-700 rounded-lg pl-3 pr-8 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
            >
              <option value="all">All Status</option>
              <option value="unread">Unread Only</option>
              <option value="read">Read Only</option>
            </select>
          </div>
          <div className="relative">
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="appearance-none bg-slate-800 border border-slate-700 rounded-lg pl-3 pr-8 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm"
            >
              <option value="all">All Providers</option>
              <option value="microsoft">Microsoft</option>
              <option value="google">Google</option>
              <option value="imap">IMAP</option>
            </select>
          </div>
          <div className="relative">
            <select
              value={mailboxFilter}
              onChange={(e) => setMailboxFilter(e.target.value)}
              className="appearance-none bg-slate-800 border border-slate-700 rounded-lg pl-3 pr-8 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer shadow-sm max-w-[140px] truncate"
            >
              <option value="all">All Mailboxes</option>
              {accounts
                .filter(a => a.status !== "disconnected")
                .map(acc => (
                  <option key={acc.id} value={acc.id}>
                    {acc.email}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </div>

      {emails.length === 0 ? (
        <div className="text-center py-16 px-6 glass-card rounded-xl border border-slate-700">
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
                  handleClearSearch();
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
          <div className={`space-y-2 md:col-span-3 ${selectedEmail ? "hidden md:block" : "block"}`}>
            <h3 className="text-[10px] uppercase tracking-wider font-bold text-slate-400 mb-2 px-1">
              Aggregated Emails
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
                        ? "bg-slate-800/90 border-indigo-500/50 shadow-md shadow-indigo-950/20"
                        : "border-slate-700/50"
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

                    <div className="flex items-center justify-between border-t border-slate-700/50 pt-2 text-[8px] tracking-wider uppercase font-bold text-slate-500">
                      <span>Inbox: {accountEmail}</span>
                      {email.has_attachment && (
                        <span className="bg-slate-800 border border-slate-700 px-1 rounded text-cyan-400">
                          📎 Attachment
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-700 pt-4 mt-4 text-xs text-slate-400 px-1">
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
    </div>
  );
}
