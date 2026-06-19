import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { sourceWins, activeConflicts } from "../lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Lock, AlertCircle, GitBranch, Shield } from "lucide-react";
import { KpiCard } from "src/components/ui/kpi-card";

const MOCK_WINS: Record<string, { total_attributes: number; pct: number; attributes: string[] }> = {
  KYC:  { total_attributes: 4200, pct: 0.48, attributes: ["kyc_status","kyc_tier","nationality","is_pep","is_sanctioned","id_number"] },
  CBS:  { total_attributes: 2100, pct: 0.24, attributes: ["date_of_birth","address_line1","city","postcode"] },
  RISK: { total_attributes: 1400, pct: 0.16, attributes: ["risk_rating","risk_score","aml_flag","fraud_flag"] },
  CRM:  { total_attributes: 1050, pct: 0.12, attributes: ["email","phone","first_name","last_name","country"] },
};
const MOCK_CONFLICTS = [
  { customer_id: "cust-0042", attribute_name: "phone",       a: "+447911123456",    b: "(555) 123-4567",      resolution: "KYC wins (trust 1.00)",        lock: false },
  { customer_id: "cust-0117", attribute_name: "date_of_birth", a: "1978-05-22",    b: "22/05/1978",          resolution: "KYC wins (trust 1.00)",        lock: false },
  { customer_id: "cust-0238", attribute_name: "is_pep",       a: "true",           b: "false",               resolution: "REGULATORY LOCK → KYC",        lock: true  },
  { customer_id: "cust-0391", attribute_name: "address_line1",a: "123 HIGH STREET", b: "123 High St, Flat 4", resolution: "CBS wins (recency 0.95)",       lock: false },
  { customer_id: "cust-0512", attribute_name: "risk_rating",  a: "CRITICAL",       b: "HIGH",                resolution: "RISK wins (trust 0.90)",        lock: false },
];
const SRC_COLORS: Record<string, string> = { KYC:"#6366f1", CBS:"#8b5cf6", RISK:"#f59e0b", CRM:"#22c55e" };

type Tab = "flow"|"wins"|"conflicts";

export default function LineageVisualizer() {
  const [wins, setWins]           = useState<any>(MOCK_WINS);
  const [conflicts, setConflicts] = useState<any[]>(MOCK_CONFLICTS);
  const [tab, setTab]             = useState<Tab>("flow");

  useEffect(() => {
    sourceWins().then(setWins).catch(() => setWins(MOCK_WINS));
    activeConflicts().then((d: any) => setConflicts(d.conflicts ?? MOCK_CONFLICTS)).catch(() => setConflicts(MOCK_CONFLICTS));
  }, []);

  const barData = Object.entries(wins).map(([src, d]: any) => ({ name: src, wins: d.total_attributes }));

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-slate-50">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Lineage Visualizer</h1>
          <p className="text-slate-500 text-sm mt-0.5">Attribute survivorship across {Object.keys(wins).length} source systems</p>
        </div>
      </motion.div>

      <div className="grid grid-cols-4 gap-4">
        {Object.entries(wins).map(([src, d]: any, i) => (
          <KpiCard key={src} label={`${src} Attribute Wins`} value={d.total_attributes}
            color={(["indigo","purple","amber","green"] as const)[i]} delay={i*0.08}
            description={`${(d.pct*100).toFixed(0)}% of all attrs`}
            icon={src === "KYC" ? <Shield size={18} /> : <GitBranch size={18} />} />
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-white border border-slate-100 rounded-xl p-1 shadow-sm w-fit">
        {(["flow","wins","conflicts"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}>
            {t === "flow" ? "Lineage Flow" : t === "wins" ? "Source Wins" : "Conflicts"}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === "flow" && (
          <motion.div key="flow" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }} className="space-y-4">
            {/* Flow diagram */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-5">Data Flow — Sources → Survivorship → Golden Record</h2>
              <div className="flex items-center gap-3">
                {/* Source nodes */}
                <div className="space-y-2">
                  {Object.keys(MOCK_WINS).map((src, i) => (
                    <motion.div key={src}
                      initial={{ opacity:0, x:-20 }} animate={{ opacity:1, x:0 }} transition={{ delay: i*0.1 }}
                      className="flex items-center justify-center w-16 h-10 rounded-xl text-white text-xs font-bold shadow-md"
                      style={{ backgroundColor: SRC_COLORS[src] }}>
                      {src}
                    </motion.div>
                  ))}
                </div>

                {/* Arrows */}
                <div className="space-y-2">
                  {Object.keys(MOCK_WINS).map((src, i) => (
                    <motion.div key={src}
                      initial={{ scaleX:0 }} animate={{ scaleX:1 }} transition={{ delay: 0.2+i*0.1 }}
                      className="flex items-center origin-left h-10">
                      <div className="w-12 h-px" style={{ backgroundColor: SRC_COLORS[src] }} />
                      <div className="w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-8" style={{ borderLeftColor: SRC_COLORS[src] }} />
                    </motion.div>
                  ))}
                </div>

                {/* Survivorship engine */}
                <motion.div initial={{ opacity:0, scale:0.9 }} animate={{ opacity:1, scale:1 }} transition={{ delay:0.5 }}
                  className="bg-slate-900 rounded-2xl p-5 text-white w-52 shadow-xl">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Survivorship Engine</p>
                  <div className="space-y-1.5 text-xs text-slate-300">
                    <p>trust_weight <span className="text-indigo-400 font-bold">× 0.50</span></p>
                    <p>recency_score <span className="text-purple-400 font-bold">× 0.30</span></p>
                    <p>completeness <span className="text-blue-400 font-bold">× 0.20</span></p>
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <p className="flex items-center gap-1.5 text-amber-400 font-semibold">
                        <Lock size={10} /> REGULATORY LOCK
                      </p>
                      <p className="text-slate-400 text-xs mt-0.5">KYC/PEP/Sanctions always from KYC</p>
                    </div>
                  </div>
                </motion.div>

                {/* Arrow out */}
                <motion.div initial={{ scaleX:0 }} animate={{ scaleX:1 }} transition={{ delay:0.7 }} className="origin-left">
                  <div className="flex items-center">
                    <div className="w-10 h-px bg-indigo-400" />
                    <div className="w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-8 border-l-indigo-400" />
                  </div>
                </motion.div>

                {/* Golden record */}
                <motion.div initial={{ opacity:0, scale:0.8 }} animate={{ opacity:1, scale:1 }} transition={{ delay:0.8, type:"spring" }}
                  className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-2xl px-5 py-4 text-white text-center shadow-xl shadow-indigo-200">
                  <p className="text-xs text-indigo-200 mb-0.5">Output</p>
                  <p className="text-base font-bold">Golden Record</p>
                  <p className="text-xs text-indigo-300 mt-0.5">5,000 entities</p>
                </motion.div>
              </div>
            </div>

            {/* Attribute groups */}
            <div className="grid grid-cols-2 gap-4">
              {[
                { title: "Regulatory Lock Attributes", attrs: ["kyc_status","kyc_tier","is_pep","is_sanctioned","pep_type","sanctions_list","kyc_verified_at"], lock: true },
                { title: "Personal Details", attrs: ["first_name","last_name","date_of_birth","nationality","gender","id_type","id_number"], lock: false },
                { title: "Contact Information", attrs: ["email","phone","address_line1","city","postcode","country"], lock: false },
                { title: "Risk Profile", attrs: ["risk_rating","risk_score","aml_flag","fraud_flag","credit_score"], lock: false },
              ].map((g, i) => (
                <motion.div key={g.title} initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.9+i*0.08 }}
                  className={`bg-white rounded-xl border shadow-sm p-4 ${g.lock ? "border-amber-300 bg-amber-50/30" : "border-slate-100"}`}>
                  <div className="flex items-center gap-2 mb-3">
                    {g.lock && <Lock size={13} className="text-amber-500" />}
                    <p className="text-sm font-semibold text-slate-700">{g.title}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {g.attrs.map((a) => (
                      <span key={a} className={`text-xs px-2 py-0.5 rounded-md font-medium ${g.lock ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>{a}</span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {tab === "wins" && (
          <motion.div key="wins" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">Attribute Wins by Source</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} barSize={60}>
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize:13, fill:"#64748b" }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize:11, fill:"#94a3b8" }} />
                <Tooltip formatter={(v) => [v, "Attributes Won"]} contentStyle={{ borderRadius:12, border:"1px solid #e2e8f0" }} />
                <Bar dataKey="wins" radius={[8,8,0,0]}>
                  {barData.map((d,i) => <Cell key={i} fill={SRC_COLORS[d.name]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {tab === "conflicts" && (
          <motion.div key="conflicts" initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-10 }}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="text-left px-5 py-3">Customer</th>
                  <th className="text-left px-4 py-3">Attribute</th>
                  <th className="px-4 py-3">Source A</th>
                  <th className="px-4 py-3">Source B</th>
                  <th className="text-left px-4 py-3">Resolution</th>
                  <th className="px-4 py-3">Lock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {conflicts.map((c, i) => (
                  <motion.tr key={i}
                    initial={{ opacity:0, x:-10 }} animate={{ opacity:1, x:0 }} transition={{ delay:i*0.05 }}
                    className={`hover:bg-slate-50 transition-colors ${c.lock ? "bg-amber-50/40" : ""}`}>
                    <td className="px-5 py-3 font-mono text-xs text-indigo-600 font-semibold">{c.customer_id}</td>
                    <td className="px-4 py-3 font-medium text-slate-700">{c.attribute_name}</td>
                    <td className="px-4 py-3 text-center font-mono text-xs text-slate-600 bg-blue-50/50">{c.a}</td>
                    <td className="px-4 py-3 text-center font-mono text-xs text-slate-600 bg-purple-50/50">{c.b}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{c.resolution}</td>
                    <td className="px-4 py-3 text-center">
                      {c.lock && <Lock size={13} className="text-amber-500 mx-auto" />}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
