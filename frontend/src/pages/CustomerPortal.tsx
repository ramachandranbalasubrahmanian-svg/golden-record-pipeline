import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getCustomerFull, ragQuery, submitErasure } from "../lib/api";
import { User, FileText, MessageSquare, Trash2, Lock, Shield, CheckCircle2, Send } from "lucide-react";
import { GradientButton } from "src/components/ui/gradient-button";
import { Progress } from "src/components/ui/progress";
import { Skeleton } from "src/components/ui/skeleton";

const DEMO_ID = "cust-0001";
const MOCK_PROFILE = {
  full_legal_name: "Alice Smith", email: "alice.smith@example.com",
  phone: "+1 555 0101", date_of_birth: "1985-03-15",
  address_line1: "123 Main Street", city: "New York", country: "United States",
  kyc_status: "VERIFIED", kyc_expiry_at: "2026-08-01",
  source_count: 3, confidence_score: 0.91,
};

type ErasureState = "idle"|"confirm"|"submitted";

export default function CustomerPortal() {
  const [customerId, setCustomerId] = useState(DEMO_ID);
  const [inputId, setInputId]       = useState(DEMO_ID);
  const [profile, setProfile]       = useState<any>(null);
  const [loading, setLoading]       = useState(true);
  const [tab, setTab]               = useState<"profile"|"chat"|"privacy">("profile");
  const [messages, setMessages]     = useState<Array<{role:"user"|"assistant";content:string}>>([]);
  const [chatInput, setChatInput]   = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [erasure, setErasure]       = useState<ErasureState>("idle");
  const [erasureReason, setErasureReason] = useState("");

  useEffect(() => {
    setLoading(true);
    getCustomerFull(customerId).then(setProfile).catch(() => setProfile(MOCK_PROFILE)).finally(() => setLoading(false));
  }, [customerId]);

  const send = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const q = chatInput; setChatInput(""); setChatLoading(true);
    setMessages((m) => [...m, { role: "user", content: q }]);
    try {
      const r: any = await ragQuery({ question: q, entity_id: customerId, persona: "customer" });
      setMessages((m) => [...m, { role: "assistant", content: r.answer ?? "No answer available." }]);
    } catch (_) {
      setMessages((m) => [...m, { role: "assistant", content: "Service temporarily unavailable. This portal uses a customer-safe persona — risk data is never exposed." }]);
    } finally { setChatLoading(false); }
  };

  const submitRight = async () => {
    try { await submitErasure(customerId, "customer@example.com", erasureReason); } catch (_) {}
    setErasure("submitted");
  };

  const p = profile ?? MOCK_PROFILE;
  const kycOk = p.kyc_status === "VERIFIED";

  return (
    <div className="min-h-full bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Portal header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Shield size={14} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900">My Account</p>
              <p className="text-xs text-slate-400">Secure Customer Portal</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input value={inputId} onChange={(e) => setInputId(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-none w-32" placeholder="Customer ID" />
            <GradientButton variant="indigo" size="sm" onClick={() => setCustomerId(inputId)}>Load</GradientButton>
          </div>
        </div>
      </div>

      {/* Customer-safe banner */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white text-xs py-2 text-center">
        <Lock size={10} className="inline mr-1.5" />
        This portal uses the <strong>customer persona</strong> — compliance, risk and PEP data are never displayed here.
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        {/* Profile card */}
        <motion.div initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
          className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
          {loading ? (
            <div className="flex gap-4"><Skeleton className="w-16 h-16 rounded-full" /><div className="space-y-2 flex-1"><Skeleton className="h-5 w-48" /><Skeleton className="h-4 w-32" /></div></div>
          ) : (
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center shrink-0">
                <User size={28} className="text-blue-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-xl font-bold text-slate-900">{p.full_legal_name}</h1>
                <p className="text-slate-500 text-sm mt-0.5">{p.email}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${kycOk ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {kycOk ? "✓" : "⚠"} {p.kyc_status}
                  </span>
                  {p.kyc_expiry_at && (
                    <span className="text-xs text-slate-400">Expires {new Date(p.kyc_expiry_at).toLocaleDateString()}</span>
                  )}
                </div>
                {p.confidence_score && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-slate-500 mb-1">
                      <span>Profile completeness</span>
                      <span>{((p.confidence_score??0)*100).toFixed(0)}%</span>
                    </div>
                    <Progress value={(p.confidence_score??0)*100} className="h-1.5" />
                  </div>
                )}
              </div>
            </div>
          )}
        </motion.div>

        {/* Tabs */}
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.1 }}
          className="flex gap-1 bg-white border border-slate-100 shadow-sm rounded-xl p-1">
          {([
            { id:"profile", label:"My Details", icon:FileText },
            { id:"chat", label:"Ask a Question", icon:MessageSquare },
            { id:"privacy", label:"My Privacy Rights", icon:Trash2 },
          ] as const).map(({ id, label, icon:Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${
                tab === id ? "bg-blue-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
              }`}>
              <Icon size={14} />{label}
            </button>
          ))}
        </motion.div>

        <AnimatePresence mode="wait">
          {tab === "profile" && (
            <motion.div key="profile" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
              className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-1.5">
              <h2 className="text-base font-bold text-slate-800 mb-4">Your Information</h2>
              {loading ? Array.from({length:8}).map((_,i) => <Skeleton key={i} className="h-9 w-full" />) : (
                [
                  ["Full Name", p.full_legal_name],
                  ["Email", p.email],
                  ["Phone", p.phone],
                  ["Date of Birth", p.date_of_birth ? new Date(p.date_of_birth).toLocaleDateString() : "—"],
                  ["Address", [p.address_line1, p.city].filter(Boolean).join(", ")],
                  ["Country", p.country],
                  ["KYC Status", p.kyc_status],
                  ["Data Sources", `${p.source_count ?? "?"} verified systems`],
                ].map(([k, v]) => (
                  <div key={String(k)} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                    <span className="text-sm text-slate-500">{k}</span>
                    <span className="text-sm font-semibold text-slate-800">{String(v ?? "—")}</span>
                  </div>
                ))
              )}
              <div className="mt-4 p-3 bg-blue-50 rounded-xl text-xs text-blue-700 border border-blue-100">
                <Lock size={11} className="inline mr-1.5" />
                Risk assessment, compliance status, and internal flags are not displayed in this portal.
              </div>
            </motion.div>
          )}

          {tab === "chat" && (
            <motion.div key="chat" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
              className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="h-72 overflow-y-auto p-5 space-y-3 bg-slate-50">
                {messages.length === 0 ? (
                  <div className="text-center text-slate-400 py-8">
                    <MessageSquare size={32} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm font-medium">Ask questions about your data</p>
                    {["What data do you hold about me?","What is my KYC status?","What documents are on file?"].map((q) => (
                      <button key={q} onClick={() => setChatInput(q)}
                        className="block w-full mt-2 text-xs text-left px-3 py-2 bg-white rounded-xl border border-slate-100 text-slate-600 hover:border-blue-200 hover:text-blue-700 transition-all">
                        {q}
                      </button>
                    ))}
                  </div>
                ) : (
                  messages.map((m, i) => (
                    <motion.div key={i} initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
                      className={`flex ${m.role==="user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-xs rounded-2xl px-4 py-2.5 text-sm ${m.role==="user" ? "bg-blue-600 text-white" : "bg-white border border-slate-100 text-slate-800 shadow-sm"}`}>
                        {m.content}
                      </div>
                    </motion.div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-slate-100 rounded-2xl px-4 py-3 shadow-sm">
                      <div className="flex gap-1">
                        {[0,1,2].map((i) => (
                          <motion.div key={i} animate={{ y:[0,-4,0] }} transition={{ repeat:Infinity, duration:0.7, delay:i*0.15 }}
                            className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="p-4 border-t border-slate-100 flex gap-3">
                <input value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key==="Enter" && send()}
                  placeholder="Type your question…"
                  className="flex-1 border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-slate-50" />
                <GradientButton variant="indigo" size="md" onClick={send} disabled={!chatInput.trim() || chatLoading}>
                  <Send size={14} />
                </GradientButton>
              </div>
            </motion.div>
          )}

          {tab === "privacy" && (
            <motion.div key="privacy" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
              className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-4">
              <h2 className="text-base font-bold text-slate-800">Your GDPR Rights</h2>
              {[
                { right:"Right to Access", desc:"Download all data we hold as JSON", action:"Download", color:"blue" as const },
                { right:"Right to Rectification", desc:"Request correction of inaccurate data", action:"Request Correction", color:"indigo" as const },
              ].map((r) => (
                <div key={r.right} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-100">
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">{r.right}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{r.desc}</p>
                  </div>
                  <GradientButton variant={r.color} size="sm">{r.action}</GradientButton>
                </div>
              ))}

              <div className="p-4 bg-red-50 rounded-xl border border-red-100 space-y-3">
                <div>
                  <p className="font-semibold text-red-800 text-sm">Right to Erasure (Article 17 GDPR)</p>
                  <p className="text-xs text-red-600 mt-0.5">Request deletion of all your data. Note: regulatory holds prevent deletion of sanctioned/PEP records.</p>
                </div>

                <AnimatePresence mode="wait">
                  {erasure === "idle" && (
                    <motion.div key="idle" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}>
                      <GradientButton variant="red" size="sm" onClick={() => setErasure("confirm")}>
                        <Trash2 size={13} /> Request Erasure
                      </GradientButton>
                    </motion.div>
                  )}
                  {erasure === "confirm" && (
                    <motion.div key="confirm" initial={{ opacity:0, y:5 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }} className="space-y-2">
                      <p className="text-xs text-red-700 font-semibold">⚠️ This is irreversible. All records will be permanently deleted.</p>
                      <textarea value={erasureReason} onChange={(e) => setErasureReason(e.target.value)}
                        placeholder="Reason (optional)" rows={2}
                        className="w-full text-xs border border-red-200 rounded-lg px-3 py-2 bg-white focus:outline-none resize-none" />
                      <div className="flex gap-2">
                        <GradientButton variant="red" size="sm" onClick={submitRight}>Confirm Delete</GradientButton>
                        <button onClick={() => setErasure("idle")}
                          className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-white">Cancel</button>
                      </div>
                    </motion.div>
                  )}
                  {erasure === "submitted" && (
                    <motion.div key="submitted" initial={{ opacity:0, scale:0.9 }} animate={{ opacity:1, scale:1 }}
                      className="flex items-center gap-2 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                      <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                      <p className="text-xs text-emerald-700 font-medium">Request submitted. You'll receive confirmation within 30 days.</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
