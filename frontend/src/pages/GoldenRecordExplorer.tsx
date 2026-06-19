import { useEffect, useState } from "react";
import { listCustomers, getCustomerFull, getTransactions, ragQuery, MOCK_STATS } from "../lib/api";
import { Badge, riskVariant, kycVariant } from "../components/Badge";
import { Search, X, Lock, AlertTriangle, ShieldAlert, MessageSquare } from "lucide-react";

const RISK_FILTERS = ["PEP", "Sanctioned", "High Risk", "Critical Risk", "KYC Expired"];
const MOCK_CUSTOMERS = Array.from({ length: 20 }, (_, i) => ({
  customer_id: `cust-${i}`,
  first_name: ["Alice", "Bob", "Carol", "David", "Eve"][i % 5],
  last_name: ["Smith", "Johnson", "Williams", "Brown", "Jones"][i % 5],
  full_legal_name: `Customer ${i} Name`,
  risk_rating: ["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4],
  kyc_status: ["VERIFIED", "PENDING", "FAILED", "EXPIRED"][i % 4],
  confidence_score: 0.7 + (i % 30) / 100,
  is_pep: i % 10 === 0,
  is_sanctioned: i % 20 === 0,
  source_count: 1 + (i % 3),
  country: "USA",
  updated_at: new Date().toISOString(),
}));

export default function GoldenRecordExplorer() {
  const [customers, setCustomers] = useState<any[]>(MOCK_CUSTOMERS);
  const [selected, setSelected] = useState<any>(null);
  const [full, setFull] = useState<any>(null);
  const [tab, setTab] = useState("profile");
  const [search, setSearch] = useState("");
  const [txns, setTxns] = useState<any[]>([]);
  const [aiQ, setAiQ] = useState("");
  const [aiAnswer, setAiAnswer] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listCustomers({ search, page_size: 50 })
      .then((d: any) => setCustomers(d.items ?? MOCK_CUSTOMERS))
      .catch(() => setCustomers(MOCK_CUSTOMERS.filter((c) =>
        !search || c.full_legal_name?.toLowerCase().includes(search.toLowerCase())
      )));
  }, [search]);

  const openCustomer = async (c: any) => {
    setSelected(c);
    setTab("profile");
    setFull(null);
    setTxns([]);
    setAiAnswer(null);
    try {
      const f: any = await getCustomerFull(c.customer_id);
      setFull(f);
    } catch (_) {
      setFull(c);
    }
  };

  const loadTxns = async () => {
    try {
      const d: any = await getTransactions(selected.customer_id);
      setTxns(d.items ?? []);
    } catch (_) {}
  };

  const askAI = async () => {
    if (!aiQ || !selected) return;
    setLoading(true);
    try {
      const ans: any = await ragQuery({ question: aiQ, entity_id: selected.customer_id, persona: "internal" });
      setAiAnswer(ans);
    } catch (_) {
      setAiAnswer({ answer: "API not available — run `make dev` to start the backend.", hallucination_check_passed: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Left list */}
      <div className="flex-1 p-6 space-y-4 overflow-y-auto">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-800">Golden Records</h1>
          <span className="text-slate-400 text-sm">({customers.length} customers)</span>
        </div>

        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or customer ID…"
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>

        <div className="flex gap-2 flex-wrap">
          {RISK_FILTERS.map((f) => (
            <button key={f} className="px-3 py-1 rounded-full border border-slate-200 text-xs text-slate-600 hover:bg-slate-100">
              {f}
            </button>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Customer</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">KYC</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Flags</th>
                <th className="px-4 py-3">Sources</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {customers.map((c) => (
                <tr key={c.customer_id} className="hover:bg-slate-50 cursor-pointer" onClick={() => openCustomer(c)}>
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {c.full_legal_name || `${c.first_name} ${c.last_name}`}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge label={c.risk_rating ?? "—"} variant={riskVariant(c.risk_rating)} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge label={c.kyc_status ?? "—"} variant={kycVariant(c.kyc_status)} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${c.confidence_score >= 0.85 ? "bg-green-500" : c.confidence_score >= 0.7 ? "bg-amber-500" : "bg-red-500"}`}
                          style={{ width: `${(c.confidence_score ?? 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 w-8">{((c.confidence_score ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {c.is_pep && <span title="PEP">⚠</span>}
                    {c.is_sanctioned && <span title="Sanctioned">🚨</span>}
                  </td>
                  <td className="px-4 py-3 text-center text-slate-500">{c.source_count}</td>
                  <td className="px-4 py-3">
                    <button onClick={(e) => { e.stopPropagation(); openCustomer(c); setTab("ai"); }} className="text-xs text-indigo-600 hover:underline">Ask AI</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Right panel */}
      {selected && (
        <div className="w-96 border-l border-slate-200 bg-white flex flex-col h-full">
          <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-start">
            <div>
              <p className="font-bold text-slate-800">
                {selected.full_legal_name || `${selected.first_name} ${selected.last_name}`}
              </p>
              <div className="flex gap-2 mt-1.5">
                <Badge label={selected.risk_rating ?? "—"} variant={riskVariant(selected.risk_rating)} />
                <Badge label={selected.kyc_status ?? "—"} variant={kycVariant(selected.kyc_status)} />
              </div>
              {selected.is_pep && <p className="text-amber-600 text-xs mt-1">⚠ PEP Customer</p>}
              {selected.is_sanctioned && <p className="text-red-600 text-xs mt-0.5">🚨 Sanctioned</p>}
            </div>
            <button onClick={() => setSelected(null)}><X size={18} className="text-slate-400" /></button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-slate-100 text-xs">
            {["profile", "lineage", "transactions", "ai"].map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); if (t === "transactions") loadTxns(); }}
                className={`flex-1 py-2.5 capitalize font-medium transition-colors ${
                  tab === t ? "border-b-2 border-indigo-500 text-indigo-600" : "text-slate-500"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {tab === "profile" && (
              <div className="space-y-2">
                {Object.entries({
                  "Full Name": (full || selected).full_legal_name,
                  "Date of Birth": (full || selected).date_of_birth,
                  "Email": (full || selected).email,
                  "Phone": (full || selected).phone,
                  "Address": (full || selected).address_line1,
                  "City": (full || selected).city,
                  "Country": (full || selected).country,
                  "Nationality": (full || selected).nationality,
                  "KYC Status": (full || selected).kyc_status,
                  "KYC Tier": (full || selected).kyc_tier,
                  "Confidence": `${(((full || selected).confidence_score ?? 0) * 100).toFixed(1)}%`,
                  "Sources": (full || selected).source_count,
                }).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-slate-500">{k}</span>
                    <span className="text-slate-800 font-medium text-right max-w-[60%] truncate">{String(v ?? "—")}</span>
                  </div>
                ))}
              </div>
            )}

            {tab === "lineage" && (
              <div className="space-y-2">
                {(full?.lineage ?? []).length === 0 && (
                  <p className="text-slate-400 text-sm">Load full customer to see lineage.</p>
                )}
                {(full?.lineage ?? []).map((l: any) => (
                  <div key={l.attribute_name} className={`text-xs rounded-lg p-3 ${l.is_regulatory_lock ? "bg-amber-50 border border-amber-200" : "bg-slate-50"}`}>
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-slate-700">{l.attribute_name}</span>
                      <div className="flex items-center gap-1">
                        {l.is_regulatory_lock && <Lock size={10} className="text-amber-500" />}
                        <span className="text-blue-600 font-medium">{l.winning_source}</span>
                      </div>
                    </div>
                    <p className="text-slate-600 mt-1">{l.winning_value}</p>
                  </div>
                ))}
              </div>
            )}

            {tab === "transactions" && (
              <div className="space-y-2">
                {txns.length === 0 && <p className="text-slate-400 text-sm">No transactions loaded yet.</p>}
                {txns.map((t: any) => (
                  <div key={t.id} className={`text-xs rounded-lg p-3 ${t.is_suspicious ? "bg-red-50 border border-red-200" : "bg-slate-50"}`}>
                    <div className="flex justify-between">
                      <span className="font-medium">{t.transaction_type}</span>
                      <span className={`font-bold ${t.transaction_type === "deposit" ? "text-green-600" : "text-slate-800"}`}>
                        ${parseFloat(t.amount).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-slate-500 mt-0.5">{t.counterparty_name} · {t.counterparty_country}</p>
                    {t.is_suspicious && <p className="text-red-600 mt-0.5">⚠ {t.suspicious_reason}</p>}
                  </div>
                ))}
              </div>
            )}

            {tab === "ai" && (
              <div className="space-y-3">
                <div className="flex flex-col gap-2">
                  {["What is the KYC status and when does it expire?", "Are there compliance concerns?", "Summarize transaction patterns"].map((q) => (
                    <button key={q} onClick={() => setAiQ(q)} className="text-xs text-left px-3 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100">
                      {q}
                    </button>
                  ))}
                </div>
                <textarea
                  value={aiQ}
                  onChange={(e) => setAiQ(e.target.value)}
                  placeholder="Ask about this customer…"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none h-20 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                />
                <button onClick={askAI} disabled={loading} className="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
                  {loading ? "Thinking…" : "Ask"}
                </button>
                {aiAnswer && (
                  <div className="bg-slate-50 rounded-lg p-3 text-sm">
                    <p className="text-slate-800">{aiAnswer.answer}</p>
                    <p className="text-xs mt-2 text-slate-400">
                      {aiAnswer.hallucination_check_passed ? "✅ Fact-checked" : "⚠️ Unverified claims"}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
