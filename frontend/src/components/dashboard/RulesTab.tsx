import React, { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { Account } from "../../types/dashboard";

interface RulesTabProps {
  token: string | null;
  accounts: Account[];
  rules: any[];
  rulesLoading: boolean;
  fetchData: () => void;
}

export default function RulesTab({ token, accounts, rules, rulesLoading, fetchData }: RulesTabProps) {
  const [showAddRuleForm, setShowAddRuleForm] = useState(false);
  const [newRuleScope, setNewRuleScope] = useState("global");
  const [newRuleSubject, setNewRuleSubject] = useState("");
  const [newRuleFromDomain, setNewRuleFromDomain] = useState("");
  const [newRuleFromEmail, setNewRuleFromEmail] = useState("");
  const [newRuleBody, setNewRuleBody] = useState("");
  const [newRuleTarget, setNewRuleTarget] = useState("");
  const [ruleSubmitting, setRuleSubmitting] = useState(false);

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    
    setRuleSubmitting(true);
    try {
      const payload = {
        mail_account_id: newRuleScope === "global" ? null : newRuleScope,
        condition_subject_contains: newRuleSubject || null,
        condition_from_domain: newRuleFromDomain || null,
        condition_from_email: newRuleFromEmail || null,
        condition_body_contains: newRuleBody || null,
        forward_to_email: newRuleTarget
      };
      
      const res = await fetch("/api/v1/rules", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create rule");
      }
      
      setNewRuleSubject("");
      setNewRuleFromDomain("");
      setNewRuleFromEmail("");
      setNewRuleBody("");
      setNewRuleTarget("");
      setShowAddRuleForm(false);
      fetchData(); // Refresh rules
    } catch (err) {
      console.error(err);
      alert("Error creating rule. See console.");
    } finally {
      setRuleSubmitting(false);
    }
  };

  const handleToggleRuleActive = async (ruleId: string, isActive: boolean) => {
    if (!token) return;
    try {
      const res = await fetch(`/api/v1/rules/${ruleId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ is_active: isActive })
      });
      if (!res.ok) throw new Error("Failed to update rule");
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!token) return;
    if (!confirm("Are you sure you want to delete this rule?")) return;
    
    try {
      const res = await fetch(`/api/v1/rules/${ruleId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to delete rule");
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between text-left">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-[#ededed]">Forwarding Rules</h2>
          <p className="text-[10px] text-zinc-400">
            Configure custom rules to forward incoming emails to external addresses.
          </p>
        </div>
        <button
          onClick={() => setShowAddRuleForm(!showAddRuleForm)}
          className="py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow shadow-sm shadow-black/10"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{showAddRuleForm ? "Hide Form" : "New Rule"}</span>
        </button>
      </div>

      {showAddRuleForm && (
        <form onSubmit={handleAddRule} className="p-5 rounded-xl glass border border-[#333] text-left space-y-4 mt-4">
          <h4 className="text-sm font-semibold text-white mb-2">Create New Rule</h4>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 block">Scope (Connected Account)</label>
            <select
              value={newRuleScope}
              onChange={(e) => setNewRuleScope(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-600 cursor-pointer"
            >
              <option value="global">All Connected Mailboxes (Global)</option>
              {accounts.filter(a => a.status !== "disconnected").map(acc => (
                <option key={acc.id} value={acc.id}>Only: {acc.email}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 block">Subject Contains</label>
              <input
                type="text"
                placeholder="e.g. Verification code, OTP"
                value={newRuleSubject}
                onChange={(e) => setNewRuleSubject(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 placeholder:text-slate-500 transition-shadow"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 block">From Domain</label>
              <input
                type="text"
                placeholder="e.g. netflix.com, google.com"
                value={newRuleFromDomain}
                onChange={(e) => setNewRuleFromDomain(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 placeholder:text-slate-500 transition-shadow"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 block">From Email Address</label>
              <input
                type="email"
                placeholder="e.g. info@netflix.com"
                value={newRuleFromEmail}
                onChange={(e) => setNewRuleFromEmail(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 placeholder:text-slate-500 transition-shadow"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-slate-400 block">Body Contains</label>
              <input
                type="text"
                placeholder="e.g. single-use, security code"
                value={newRuleBody}
                onChange={(e) => setNewRuleBody(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 placeholder:text-slate-500 transition-shadow"
              />
            </div>
          </div>

          <div className="space-y-1.5 pt-1">
            <label className="text-[10px] font-bold text-slate-400 block">Forward To (Target Email) *</label>
            <input
              type="email"
              required
              placeholder="e.g. customer@outlook.com"
              value={newRuleTarget}
              onChange={(e) => setNewRuleTarget(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/50 placeholder:text-slate-500 transition-shadow"
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
              className="py-1.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 text-white text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow shadow-sm shadow-black/10"
            >
              {ruleSubmitting && <Loader2 className="h-3 w-3 animate-spin mr-1 shrink-0" />}
              <span>Create Rule</span>
            </button>
          </div>
        </form>
      )}

      {rulesLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-6 w-6 text-indigo-500 animate-spin mb-2" />
          <p className="text-[10px] text-slate-400">Loading forwarding rules...</p>
        </div>
      ) : rules.length === 0 ? (
        <div className="p-8 text-center glass-card rounded-xl border border-slate-700 text-slate-400 text-xs">
          No forwarding rules defined yet. Click "New Rule" above to get started.
        </div>
      ) : (
        <div className="space-y-4 mt-4">
          {rules.map((rule) => {
            const scopeAccount = accounts.find(a => a.id === rule.mail_account_id);
            return (
              <div key={rule.id} className="p-4 rounded-xl glass-card text-left border border-[#333] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2.5 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className={`text-[9px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full ${
                      rule.mail_account_id ? "bg-[#222] border border-[#444] text-zinc-300" : "bg-indigo-950/60 border border-indigo-900/40 text-indigo-400"
                    }`}>
                      {rule.mail_account_id ? "Scoped Rule" : "Global Rule"}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {rule.mail_account_id ? `Applies to: ${scopeAccount?.email || 'Unknown Mailbox'}` : 'Applies to: All mailboxes'}
                    </span>
                  </div>

                  <div>
                    <p className="text-xs font-bold text-white flex items-center">
                      <span>Forward to:</span>
                      <span className="ml-1.5 text-indigo-400 underline decoration-indigo-800/40 select-all">{rule.forward_to_email}</span>
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {rule.condition_subject_contains && (
                      <span className="text-[10px] bg-[#1a1a1a] border border-[#333] rounded-md px-2 py-1 text-zinc-400">
                        Subject contains: <b className="text-zinc-200">"{rule.condition_subject_contains}"</b>
                      </span>
                    )}
                    {rule.condition_from_domain && (
                      <span className="text-[10px] bg-[#1a1a1a] border border-[#333] rounded-md px-2 py-1 text-zinc-400">
                        From domain: <b className="text-zinc-200">{rule.condition_from_domain}</b>
                      </span>
                    )}
                    {rule.condition_from_email && (
                      <span className="text-[10px] bg-[#1a1a1a] border border-[#333] rounded-md px-2 py-1 text-zinc-400">
                        From email: <b className="text-zinc-200">{rule.condition_from_email}</b>
                      </span>
                    )}
                    {rule.condition_body_contains && (
                      <span className="text-[10px] bg-[#1a1a1a] border border-[#333] rounded-md px-2 py-1 text-zinc-400">
                        Body contains: <b className="text-zinc-200">"{rule.condition_body_contains}"</b>
                      </span>
                    )}
                    {!rule.condition_subject_contains && !rule.condition_from_domain && !rule.condition_from_email && !rule.condition_body_contains && (
                      <span className="text-[9px] bg-emerald-950/40 border border-emerald-900/20 rounded px-1.5 py-0.5 text-emerald-400 italic">
                        Matches all incoming emails
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-4 self-end md:self-center">
                  <label className="flex items-center space-x-2 cursor-pointer select-none py-2">
                    <input
                      type="checkbox"
                      checked={rule.is_active}
                      onChange={(e) => handleToggleRuleActive(rule.id, e.target.checked)}
                      className="accent-indigo-600 rounded bg-[#111] border-[#333] focus:ring-0 cursor-pointer h-5 w-5 shrink-0"
                    />
                    <span className="text-xs font-semibold text-zinc-300">Active</span>
                  </label>
                  
                  <button
                    onClick={() => handleDeleteRule(rule.id)}
                    className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-950/30 hover:bg-rose-950/15 transition cursor-pointer"
                    title="Delete Rule"
                  >
                    <span className="text-xs font-bold">Delete</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
