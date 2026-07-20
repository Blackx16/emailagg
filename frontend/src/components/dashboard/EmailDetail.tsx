import React from "react";
import { Mail, Loader2 } from "lucide-react";
import { Account, EmailItem } from "../../types/dashboard";

interface EmailDetailProps {
  selectedEmail: EmailItem | null;
  setSelectedEmail: (email: EmailItem | null) => void;
  emailDetailLoading: boolean;
  emailDetail: any;
  emailBodyView: "html" | "text";
  setEmailBodyView: (view: "html" | "text") => void;
  accounts: Account[];
}

export default function EmailDetail({
  selectedEmail,
  setSelectedEmail,
  emailDetailLoading,
  emailDetail,
  emailBodyView,
  setEmailBodyView,
  accounts
}: EmailDetailProps) {
  return (
    <div className={`md:col-span-2 space-y-2 ${selectedEmail ? "block" : "hidden md:block"}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] uppercase tracking-widest font-bold text-slate-400 px-1">
          Email Details
        </h3>
        {selectedEmail && (
          <button
            onClick={() => setSelectedEmail(null)}
            className="md:hidden py-1 px-2.5 bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700/50 text-[10px] font-bold rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500/50 transition cursor-pointer"
          >
            ← Back to list
          </button>
        )}
      </div>

      <div className="p-5 glass-card rounded-xl text-left border border-slate-700 h-[calc(100vh-140px)] overflow-y-auto flex flex-col">
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
          <div className="space-y-4 flex-1">
            <div>
              <span className="text-[9px] uppercase tracking-wider font-black text-cyan-400 bg-cyan-950/50 border border-cyan-900/40 px-1.5 py-0.5 rounded">
                {accounts.find(a => a.id === selectedEmail.mail_account_id)?.provider || "IMAP"}
              </span>
              <h1 className="text-lg font-bold tracking-tight text-slate-100 mt-2 leading-snug">
                {selectedEmail.subject || "(No Subject)"}
              </h1>
            </div>

            <div className="border-y border-slate-700 py-3 text-xs space-y-1.5 leading-relaxed text-slate-300">
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

            {(emailDetail?.body_html || emailDetail?.body_text) && (
              <div className="flex items-center space-x-3 border-b border-slate-700/60 pb-4 mb-2">
                <button
                  onClick={() => setEmailBodyView("html")}
                  disabled={!emailDetail?.body_html}
                  className={`px-4 py-2 rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all duration-200 flex items-center space-x-2 border cursor-pointer ${
                    emailBodyView === "html"
                      ? "bg-indigo-500/10 border-indigo-500/50 text-indigo-400 shadow-sm"
                      : "bg-transparent border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 disabled:opacity-30 disabled:cursor-not-allowed"
                  }`}
                >
                  <span>🎨</span>
                  <span>HTML View</span>
                </button>
                <button
                  onClick={() => setEmailBodyView("text")}
                  disabled={!emailDetail?.body_text}
                  className={`px-4 py-2 rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all duration-200 flex items-center space-x-2 border cursor-pointer ${
                    emailBodyView === "text"
                      ? "bg-indigo-500/10 border-indigo-500/50 text-indigo-400 shadow-sm"
                      : "bg-transparent border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 disabled:opacity-30 disabled:cursor-not-allowed"
                  }`}
                >
                  <span>📄</span>
                  <span>Plain Text</span>
                </button>
              </div>
            )}

            {emailDetail?.body_html && emailBodyView === "html" ? (
              <div className="rounded-xl overflow-hidden border border-slate-700 bg-white shadow-sm mt-2">
                <iframe
                  srcDoc={`<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><base target="_blank"><style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.6;color:#1a1a1a;background:#ffffff;margin:0;padding:24px;}a{color:#0066cc;}img{max-width:100%;height:auto;}*{box-sizing:border-box;}</style></head><body>${emailDetail.body_html.replace(/`/g, '\\`')}</body></html>`}
                  sandbox="allow-same-origin"
                  className="w-full"
                  style={{ border: "none", background: "white", minHeight: "600px" }}
                  title="Email body"
                  onLoad={(e) => {
                    const target = e.target as HTMLIFrameElement;
                    if (target.contentWindow) {
                      try {
                        const contentHeight = target.contentWindow.document.documentElement.scrollHeight;
                        target.style.height = `${Math.max(600, contentHeight)}px`;
                      } catch (err) {
                        console.error("Could not resize iframe", err);
                      }
                    }
                  }}
                />
              </div>
            ) : emailDetail?.body_text && (emailBodyView === "text" || !emailDetail?.body_html) ? (
              <div className="text-xs text-slate-300 leading-relaxed bg-slate-800 border border-slate-700 p-4 rounded-xl whitespace-pre-wrap font-mono mt-2">
                {emailDetail.body_text}
              </div>
            ) : (
              <div className="space-y-2 mt-2">
                <div className="text-xs text-slate-300 leading-relaxed bg-slate-800 border border-slate-700 p-3 rounded-xl whitespace-pre-wrap font-sans">
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
  );
}
