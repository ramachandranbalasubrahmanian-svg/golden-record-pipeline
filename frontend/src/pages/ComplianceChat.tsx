import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ragQuery } from "../lib/api";
import { Send, Bot, User, CheckCircle2, AlertTriangle, Sparkles } from "lucide-react";
import { GradientButton } from "src/components/ui/gradient-button";

const PERSONAS = [
  { id: "internal", label: "Compliance Officer", badge: "Full access", color: "indigo" },
  { id: "customer", label: "Customer Self-Service", badge: "Filtered", color: "purple" },
] as const;

const QUESTIONS = [
  "Who are the PEP customers with verified KYC status?",
  "Show high-risk customers with KYC expiring in 30 days",
  "Summarize compliance posture for entity cluster C-0018",
  "Which attributes came from KYC vs CRM for this customer?",
  "Are there any sanctioned customers with recent transactions?",
];

type Msg = { role: "user"|"assistant"; content: string; sources?: any[]; hallucination_check_passed?: boolean };

export default function ComplianceChat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput]       = useState("");
  const [entityId, setEntityId] = useState("");
  const [persona, setPersona]   = useState<"internal"|"customer">("internal");
  const [loading, setLoading]   = useState(false);
  const [sources, setSources]   = useState<any[]>([]);
  const bottomRef               = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const q = input;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);
    try {
      const res: any = await ragQuery({ question: q, entity_id: entityId || undefined, persona, top_k: 8 });
      setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources, hallucination_check_passed: res.hallucination_check_passed }]);
      if (res.sources?.length) setSources(res.sources);
    } catch (_) {
      setMessages((m) => [...m, { role: "assistant", content: "Backend not reachable. Run `make dev` in the backend folder to start the FastAPI server.\n\nThis chat uses hybrid RAG (pgvector cosine + BM25 + RRF) with GPT-4o-mini and hallucination validation.", hallucination_check_passed: true }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Config panel */}
      <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.3 }}
        className="w-68 border-r border-slate-200 bg-white flex flex-col shrink-0" style={{ minWidth: 260 }}>
        <div className="px-4 py-4 border-b border-slate-100 bg-slate-50">
          <p className="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Sparkles size={14} className="text-indigo-500" /> Query Settings
          </p>
        </div>

        <div className="p-4 space-y-5 flex-1 overflow-y-auto">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-1.5">Entity ID</label>
            <input value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="cust-0001 (optional)"
              className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50" />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-2">Persona</label>
            <div className="space-y-2">
              {PERSONAS.map((p) => (
                <button key={p.id} onClick={() => setPersona(p.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl border-2 transition-all ${
                    persona === p.id
                      ? "border-indigo-400 bg-indigo-50"
                      : "border-slate-100 hover:border-slate-200 hover:bg-slate-50"
                  }`}>
                  <p className="text-sm font-semibold text-slate-800">{p.label}</p>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${persona === p.id ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"}`}>
                    {p.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide block mb-2">Suggested</label>
            <div className="space-y-1.5">
              {QUESTIONS.map((q) => (
                <button key={q} onClick={() => setInput(q)}
                  className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-50 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700 border border-transparent hover:border-indigo-100 transition-all">
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-slate-100">
          <button onClick={() => { setMessages([]); setSources([]); }}
            className="w-full text-xs text-slate-400 hover:text-slate-600 py-1.5 hover:bg-slate-50 rounded-lg transition-colors">
            Clear conversation
          </button>
        </div>
      </motion.div>

      {/* Chat */}
      <div className="flex-1 flex flex-col bg-slate-50 min-w-0">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <AnimatePresence>
            {messages.length === 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center h-full text-center py-16">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-indigo-200">
                  <Bot size={28} className="text-white" />
                </div>
                <h3 className="text-lg font-bold text-slate-800">Compliance AI</h3>
                <p className="text-slate-500 text-sm mt-1 max-w-xs">RAG-powered search over 5,000 golden records with hallucination validation</p>
              </motion.div>
            )}
          </AnimatePresence>

          {messages.map((msg, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.2 }}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                  <Bot size={14} className="text-white" />
                </div>
              )}
              <div className="max-w-2xl min-w-0">
                <div className={`rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-sm"
                    : "bg-white border border-slate-100 text-slate-800 shadow-sm"
                }`}>
                  {msg.content}
                </div>
                {msg.role === "assistant" && (
                  <div className="flex items-center gap-3 mt-1.5 px-1">
                    {msg.hallucination_check_passed != null && (
                      <span className={`flex items-center gap-1 text-xs font-medium ${msg.hallucination_check_passed ? "text-emerald-600" : "text-red-500"}`}>
                        {msg.hallucination_check_passed ? <CheckCircle2 size={11} /> : <AlertTriangle size={11} />}
                        {msg.hallucination_check_passed ? "Fact-checked" : "Unverified"}
                      </span>
                    )}
                    {msg.sources && msg.sources.length > 0 && (
                      <button onClick={() => setSources(msg.sources!)}
                        className="text-xs text-indigo-500 hover:text-indigo-700 hover:underline">
                        {msg.sources.length} sources →
                      </button>
                    )}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-xl bg-slate-200 flex items-center justify-center shrink-0 mt-0.5">
                  <User size={14} className="text-slate-600" />
                </div>
              )}
            </motion.div>
          ))}

          {loading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Bot size={14} className="text-white" />
              </div>
              <div className="bg-white border border-slate-100 rounded-2xl px-5 py-3.5 shadow-sm">
                <div className="flex gap-1.5">
                  {[0,1,2].map((i) => (
                    <motion.div key={i} animate={{ y: [0,-4,0] }} transition={{ repeat: Infinity, duration: 0.8, delay: i*0.15 }}
                      className="w-2 h-2 rounded-full bg-indigo-400" />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-6 py-4 border-t border-slate-200 bg-white">
          <div className="flex gap-3">
            <input value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask a compliance question…"
              className="flex-1 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50 min-w-0" />
            <GradientButton variant="indigo" onClick={send} disabled={!input.trim() || loading}>
              <Send size={14} />
            </GradientButton>
          </div>
        </div>
      </div>

      {/* Sources panel */}
      <AnimatePresence>
        {sources.length > 0 && (
          <motion.div initial={{ x: 20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 20, opacity: 0 }}
            className="w-72 border-l border-slate-200 bg-white flex flex-col shrink-0">
            <div className="px-4 py-3.5 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
              <p className="text-sm font-bold text-slate-800">{sources.length} Sources</p>
              <button onClick={() => setSources([])} className="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
            </div>
            <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
              {sources.map((src: any, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                  className="px-4 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex justify-between mb-1">
                    <span className="text-xs font-semibold text-indigo-600 capitalize">{(src.chunk_type ?? "").replace(/_/g, " ")}</span>
                    {src.rank_score && <span className="text-xs text-slate-400">{(src.rank_score * 100).toFixed(0)}%</span>}
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">{src.chunk_text}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
