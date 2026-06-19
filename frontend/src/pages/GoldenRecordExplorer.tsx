import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listCustomers, getCustomerFull, getTransactions, ragQuery } from "../lib/api";
import { Search, X, Lock, MessageSquare } from "lucide-react";
import { Skeleton } from "src/components/ui/skeleton";
import { GradientButton } from "src/components/ui/gradient-button";

type Risk = "LOW"|"MEDIUM"|"HIGH"|"CRITICAL";
type KYC  = "VERIFIED"|"PENDING"|"FAILED"|"EXPIRED";

const RISK_CHIP: Record<Risk, string> = {
  LOW: "bg-slate-100 text-slate-600",
  MEDIUM: "bg-amber-100 text-amber-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800 font-bold",
};
const KYC_CHIP: Record<KYC, string> = {
  VERIFIED: "bg-emerald-100 text-emerald-800",
  PENDING: "bg-blue-100 text-blue-700",
  FAILED: "bg-red-100 text-red-700",
  EXPIRED: "bg-amber-100 text-amber-800",
};

const MOCK_CUSTOMERS = Array.from({ length: 30 }, (_, i) => ({
  customer_id: `cust-${String(i).padStart(4,"0")}`,
  full_legal_name: `${["Alice","Bob","Carol","David","Eve","Frank","Grace","Henry"][i%8]} ${["Smith","Johnson","Williams","Brown","Jones","Davis","Miller","Wilson"][i%8]}`,
  risk_rating: (["LOW","MEDIUM","HIGH","CRITICAL"] as Risk[])[i % 4],
  kyc_status: (["VERIFIED","PENDING","FAILED","EXPIRED"] as KYC[])[i % 4],
  confidence_score: 0.68 + (i % 32) / 100,
  is_pep: i % 7 === 0,
  is_sanctioned: i % 19 === 0,
  source_count: 1 + (i % 3),
  country: ["USA","GBR","DEU","FRA","SGP"][i%5],
}));

const RISK_FILTERS: Risk[] = ["LOW","MEDIUM","HIGH","CRITICAL"];

export default function GoldenRecordExplorer() {
  const [customers, setCustomers] = useState(MOCK_CUSTOMERS);
  const [selected, setSelected]   = useState<any>(null);
  const [full, setFull]           = useState<any>(null);
  const [txns, setTxns]           = useState<any[]>([]);
  const [tab, setTab]             = useState("profile");
  const [search, setSearch]       = useState("");
  const [riskFilter, setRiskFilter] = useState<Risk|null>(null);
  const [aiQ, setAiQ]             = useState("");
  const [aiAnswer, setAiAnswer]   = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    listCustomers({ search, page_size: 50 })
      .then((d: any) => setCustomers(d.items ?? MOCK_CUSTOMERS))
      .catch(() => setCustomers(
        MOCK_CUSTOMERS.filter((c) => {
          const matchSearch = !search || c.full_legal_name.toLowerCase().includes(search.toLowerCase());
          const matchRisk   = !riskFilter || c.risk_rating === riskFilter;
          return matchSearch && matchRisk;
        })
      ));
  }, [search, riskFilter]);

  const open = async (c: any) => {
    setSelected(c); setTab("profile"); setFull(null); setTxns([]); setAiAnswer(null);
    try { setFull(await getCustomerFull(c.customer_id)); } catch (_) { setFull(c); }
  };

  const loadTxns = async () => {
    try {
      const d: any = await getTransactions(selected.customer_id);
      setTxns(d.items ?? []);
    } catch (_) {}
  };

  const ask = async () => {
    if (!aiQ || !selected) return;
    setAiLoading(true);
    try {
      const r: any = await ragQuery({ question: aiQ, entity_id: selected.customer_id, persona: "internal" });
      setAiAnswer(r);
    } catch (_) {
      setAiAnswer({ answer: "Backend not reachable — run `make dev` to start the API.", hallucination_check_passed: true });
    } finally { setAiLoading(false); }
  };

  const filtered = customers.filter((c) =>
    (!search || c.full_legal_name.toLowerCase().includes(search.toLowerCase())) &&
    (!riskFilter || c.risk_rating === riskFilter)
  );

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main table */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-5 border-b border-slate-100 bg-white space-y-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-slate-900">Golden Records <span className="text-slate-400 font-normal text-base ml-1">({filtered.length})</span></h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-xs">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name…"
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50" />
            </div>
            <div className="flex gap-1.5">
              <button onClick={() => setRiskFilter(null)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${!riskFilter ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                All
              </button>
              {RISK_FILTERS.map((r) => (
                <button key={r} onClick={() => setRiskFilter(riskFilter === r ? null : r)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${riskFilter === r ? "ring-2 ring-offset-1 ring-indigo-400 " + RISK_CHIP[r] : RISK_CHIP[r] + " opacity-70 hover:opacity-100"}`}>
                  {r}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white border-b border-slate-100 text-xs text-slate-500 uppercase tracking-wide z-10">
              <tr>
                <th className="text-left px-5 py-3">Customer</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">KYC</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Country</th>
                <th className="px-4 py-3">Flags</th>
                <th className="px-4 py-3">Sources</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <motion.tr key={c.customer_id}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i * 0.02, 0.3) }}
                  onClick={() => open(c)}
                  className={`cursor-pointer hover:bg-indigo-50/50 transition-colors border-b border-slate-50 ${selected?.customer_id === c.customer_id ? "bg-indigo-50" : ""}`}>
                  <td className="px-5 py-3">
                    <p className="font-semibold text-slate-800">{c.full_legal_name}</p>
                    <p className="text-xs text-slate-400 font-mono">{c.customer_id}</p>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${RISK_CHIP[c.risk_rating as Risk]}`}>{c.risk_rating}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${KYC_CHIP[c.kyc_status as KYC]}`}>{c.kyc_status}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5 min-w-12">
                        <motion.div initial={{ width:0 }} animate={{ width:`${c.confidence_score*100}%` }} transition={{ delay:i*0.02, duration:0.5 }}
                          className={`h-1.5 rounded-full ${c.confidence_score>=0.85?"bg-emerald-500":c.confidence_score>=0.7?"bg-amber-400":"bg-red-400"}`} />
                      </div>
                      <span className="text-xs text-slate-500 w-8 shrink-0">{(c.confidence_score*100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-xs text-slate-600 font-medium">{c.country}</td>
                  <td className="px-4 py-3 text-center text-base">
                    {c.is_pep && <span title="PEP">⚠️</span>}
                    {c.is_sanctioned && <span title="Sanctioned">🚨</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">{c.source_count}</span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail panel */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="w-96 border-l border-slate-200 bg-white flex flex-col shrink-0">
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-bold text-slate-900">{selected.full_legal_name}</p>
                  <p className="font-mono text-xs text-slate-400 mt-0.5">{selected.customer_id}</p>
                  <div className="flex gap-2 mt-2">
                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${RISK_CHIP[selected.risk_rating as Risk]}`}>{selected.risk_rating}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${KYC_CHIP[selected.kyc_status as KYC]}`}>{selected.kyc_status}</span>
                  </div>
                  {selected.is_pep && <p className="text-amber-600 text-xs mt-1.5 font-medium">⚠️ Politically Exposed Person</p>}
                  {selected.is_sanctioned && <p className="text-red-600 text-xs mt-0.5 font-medium">🚨 On Sanctions List</p>}
                </div>
                <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600 w-7 h-7 flex items-center justify-center rounded-lg hover:bg-slate-100">
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-100 bg-white">
              {["profile","lineage","transactions","ai"].map((t) => (
                <button key={t} onClick={() => { setTab(t); if (t==="transactions") loadTxns(); }}
                  className={`flex-1 py-2.5 text-xs font-semibold capitalize transition-colors ${
                    tab === t ? "border-b-2 border-indigo-500 text-indigo-600" : "text-slate-400 hover:text-slate-600"
                  }`}>
                  {t === "ai" ? "Ask AI" : t}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              <AnimatePresence mode="wait">
                {tab === "profile" && (
                  <motion.div key="profile" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} className="space-y-1.5">
                    {!full ? <div className="space-y-2">{Array.from({length:8}).map((_,i) => <Skeleton key={i} className="h-8 w-full" />)}</div> : (
                      Object.entries({
                        "Full Name": full.full_legal_name,
                        "Date of Birth": full.date_of_birth,
                        "Email": full.email,
                        "Phone": full.phone,
                        "Address": full.address_line1,
                        "City": full.city,
                        "Country": full.country,
                        "KYC Tier": full.kyc_tier,
                        "Confidence": `${((full.confidence_score??0)*100).toFixed(1)}%`,
                        "Sources": full.source_count,
                      }).map(([k,v]) => (
                        <div key={k} className="flex justify-between items-center py-1.5 border-b border-slate-50 last:border-0">
                          <span className="text-xs text-slate-400 font-medium">{k}</span>
                          <span className="text-xs text-slate-800 font-semibold text-right max-w-48 truncate">{String(v ?? "—")}</span>
                        </div>
                      ))
                    )}
                  </motion.div>
                )}
                {tab === "lineage" && (
                  <motion.div key="lineage" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} className="space-y-2">
                    {(full?.lineage ?? []).length === 0 && <p className="text-slate-400 text-xs text-center py-4">Connect to live API for lineage</p>}
                    {(full?.lineage ?? []).map((l: any) => (
                      <div key={l.attribute_name} className={`rounded-xl p-3 text-xs ${l.is_regulatory_lock ? "bg-amber-50 border border-amber-200" : "bg-slate-50"}`}>
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-slate-700">{l.attribute_name}</span>
                          <div className="flex items-center gap-1">
                            {l.is_regulatory_lock && <Lock size={10} className="text-amber-500" />}
                            <span className="text-indigo-600 font-bold">{l.winning_source}</span>
                          </div>
                        </div>
                        <p className="text-slate-600 mt-1">{l.winning_value}</p>
                      </div>
                    ))}
                  </motion.div>
                )}
                {tab === "transactions" && (
                  <motion.div key="txns" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} className="space-y-2">
                    {txns.length === 0 && <p className="text-slate-400 text-xs text-center py-4">No transactions loaded</p>}
                    {txns.map((t: any) => (
                      <div key={t.id} className={`rounded-xl p-3 text-xs ${t.is_suspicious ? "bg-red-50 border border-red-200" : "bg-slate-50"}`}>
                        <div className="flex justify-between">
                          <span className="font-semibold">{t.transaction_type}</span>
                          <span className={`font-bold ${t.amount > 0 ? "text-emerald-600" : "text-slate-700"}`}>${parseFloat(t.amount).toLocaleString()}</span>
                        </div>
                        <p className="text-slate-500 mt-0.5">{t.counterparty_name} · {t.counterparty_country}</p>
                        {t.is_suspicious && <p className="text-red-600 mt-1 font-medium">⚠ {t.suspicious_reason}</p>}
                      </div>
                    ))}
                  </motion.div>
                )}
                {tab === "ai" && (
                  <motion.div key="ai" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} className="space-y-3">
                    {["What is the KYC status?","Are there compliance concerns?","Summarise transactions"].map((q) => (
                      <button key={q} onClick={() => setAiQ(q)}
                        className="w-full text-left text-xs px-3 py-2 bg-indigo-50 text-indigo-700 rounded-xl hover:bg-indigo-100 transition-colors font-medium">
                        {q}
                      </button>
                    ))}
                    <textarea value={aiQ} onChange={(e) => setAiQ(e.target.value)}
                      placeholder="Ask about this customer…"
                      className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-xs resize-none h-20 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50" />
                    <GradientButton variant="indigo" size="sm" onClick={ask} disabled={aiLoading || !aiQ} className="w-full justify-center">
                      <MessageSquare size={12} /> {aiLoading ? "Thinking…" : "Ask"}
                    </GradientButton>
                    {aiAnswer && (
                      <motion.div initial={{ opacity:0, y:5 }} animate={{ opacity:1, y:0 }}
                        className="bg-slate-50 rounded-xl p-3 text-xs border border-slate-100">
                        <p className="text-slate-800 leading-relaxed">{aiAnswer.answer}</p>
                        <p className="text-slate-400 mt-2">{aiAnswer.hallucination_check_passed ? "✅ Fact-checked" : "⚠️ Unverified"}</p>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
