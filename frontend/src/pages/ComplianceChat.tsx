import { useEffect, useRef, useState } from "react";
import { ragQuery, getStats, MOCK_STATS } from "../lib/api";
import { Send, User, Bot, AlertTriangle, ExternalLink } from "lucide-react";

const DEMO_QUESTIONS = [
  "Who are the PEP customers with verified KYC status?",
  "Show me high-risk customers with expiring KYC within 30 days",
  "What does the entity resolution model say about cluster C-1042?",
  "Summarize the compliance posture for customer in entity cluster C-0018",
  "Which attributes for this customer came from KYC vs CRM?",
];

const PERSONAS = [
  { id: "internal", label: "Compliance Officer", description: "Full access including risk/PEP data" },
  { id: "customer", label: "Customer Self-Service", description: "Filtered — no risk or PEP data shown" },
];

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: any[];
  hallucination_check_passed?: boolean;
  entity_id?: string;
};

export default function ComplianceChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [entityId, setEntityId] = useState("");
  const [persona, setPersona] = useState("internal");
  const [loading, setLoading] = useState(false);
  const [selectedSources, setSelectedSources] = useState<any[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: any = await ragQuery({
        question: input,
        entity_id: entityId || undefined,
        persona,
        top_k: 8,
      });
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer ?? "No answer returned.",
          sources: res.sources ?? [],
          hallucination_check_passed: res.hallucination_check_passed,
          entity_id: res.entity_id,
        },
      ]);
      if (res.sources?.length) setSelectedSources(res.sources);
    } catch (_) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "Backend not reachable. Run `make dev` to start the FastAPI server, then try again.\n\n" +
            "This chat uses RAG over pgvector — hybrid cosine + BM25 retrieval with GPT-4o-mini generation and hallucination validation.",
          hallucination_check_passed: true,
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Left config panel */}
      <div className="w-72 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-4 py-4 border-b border-slate-100">
          <p className="font-semibold text-slate-800 text-sm mb-3">Query Configuration</p>
          <label className="block text-xs text-slate-500 mb-1">Entity ID (optional)</label>
          <input
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            placeholder="e.g. cust-0001"
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>

        <div className="px-4 py-4 border-b border-slate-100">
          <p className="text-xs text-slate-500 mb-2">Persona</p>
          <div className="space-y-2">
            {PERSONAS.map((p) => (
              <label key={p.id} className={`flex items-start gap-2.5 cursor-pointer rounded-lg p-2.5 transition-colors ${persona === p.id ? "bg-indigo-50 border border-indigo-200" : "border border-transparent hover:bg-slate-50"}`}>
                <input type="radio" name="persona" value={p.id} checked={persona === p.id} onChange={() => setPersona(p.id)} className="mt-0.5 accent-indigo-600" />
                <div>
                  <p className="text-sm font-medium text-slate-800">{p.label}</p>
                  <p className="text-xs text-slate-500">{p.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="px-4 py-4 border-b border-slate-100">
          <p className="text-xs text-slate-500 mb-2">Suggested Questions</p>
          <div className="space-y-1.5">
            {DEMO_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => setInput(q)}
                className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-50 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() => setMessages([])}
          className="mx-4 mt-4 px-4 py-2 text-xs text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          Clear conversation
        </button>
      </div>

      {/* Middle chat */}
      <div className="flex-1 flex flex-col bg-slate-50">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <p className="text-4xl mb-3">🔍</p>
                <p className="text-slate-600 font-medium">Compliance Query Interface</p>
                <p className="text-slate-400 text-sm mt-1">RAG-powered search over golden records</p>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 mt-1">
                  <Bot size={14} className="text-white" />
                </div>
              )}
              <div className={`max-w-xl ${msg.role === "user" ? "order-first" : ""}`}>
                <div className={`rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${msg.role === "user" ? "bg-indigo-600 text-white" : "bg-white border border-slate-200 text-slate-800"}`}>
                  {msg.content}
                </div>
                {msg.role === "assistant" && (
                  <div className="flex items-center gap-3 mt-1.5 px-1">
                    {msg.hallucination_check_passed != null && (
                      <span className={`text-xs ${msg.hallucination_check_passed ? "text-green-600" : "text-red-600"}`}>
                        {msg.hallucination_check_passed ? "✅ Fact-checked" : "⚠️ Unverified claims"}
                      </span>
                    )}
                    {msg.sources && msg.sources.length > 0 && (
                      <button
                        onClick={() => setSelectedSources(msg.sources!)}
                        className="text-xs text-indigo-500 hover:underline"
                      >
                        {msg.sources.length} sources
                      </button>
                    )}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-slate-300 flex items-center justify-center shrink-0 mt-1">
                  <User size={14} className="text-slate-600" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                <Bot size={14} className="text-white" />
              </div>
              <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              placeholder="Ask a compliance question…"
              className="flex-1 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              onClick={send}
              disabled={!input.trim() || loading}
              className="px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Right sources panel */}
      {selectedSources.length > 0 && (
        <div className="w-72 border-l border-slate-200 bg-white overflow-y-auto">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-800">Sources ({selectedSources.length})</p>
            <button onClick={() => setSelectedSources([])} className="text-slate-400 hover:text-slate-600 text-xs">✕</button>
          </div>
          <div className="divide-y divide-slate-100">
            {selectedSources.map((src: any, i: number) => (
              <div key={i} className="px-4 py-3">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs font-medium text-slate-800 capitalize">{(src.chunk_type ?? "").replace(/_/g, " ")}</span>
                  <span className="text-xs text-slate-400">{src.rank_score ? `${(src.rank_score * 100).toFixed(0)}%` : ""}</span>
                </div>
                <p className="text-xs text-slate-600 line-clamp-4">{src.chunk_text}</p>
                {src.entity_id && <p className="text-xs text-indigo-500 mt-1">{src.entity_id}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
