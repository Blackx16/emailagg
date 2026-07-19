import React from "react";
import { Mail, RefreshCw, LogOut } from "lucide-react";

interface HeaderProps {
  user: any;
  refreshing: boolean;
  fetchData: (isRefresh?: boolean) => void;
  logout: () => void;
}

export default function Header({ user, refreshing, fetchData, logout }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 glass border-b border-slate-700 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-2.5">
        <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-md">
          <Mail className="h-4.5 w-4.5 text-white" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-white tracking-wide">EmailAgg</h2>
          <p className="text-[10px] text-slate-400">Telegram Command Center</p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {user && (
          <div className="hidden xs:flex flex-col items-end mr-1">
            <div className="flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-semibold text-slate-300">ID: {user.telegram_id}</span>
            </div>
            <span className="text-[9px] uppercase tracking-widest font-black text-cyan-400 bg-cyan-950/50 border border-cyan-800/40 px-1.5 rounded">
              {user.plan} plan
            </span>
          </div>
        )}

        <button 
          onClick={() => fetchData(true)}
          disabled={refreshing}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 hover:bg-slate-800 transition duration-150 cursor-pointer"
          title="Refresh Data"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin text-indigo-400" : ""}`} />
        </button>

        <button
          onClick={logout}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-900/30 hover:bg-rose-900/10 transition duration-150 cursor-pointer"
          title="Log Out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
