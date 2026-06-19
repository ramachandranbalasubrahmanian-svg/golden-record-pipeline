import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts";
import { RefreshCw, TrendingUp, AlertCircle, CheckCircle2 } from "lucide-react";
import { KpiCard } from "src/components/ui/kpi-card";
import { GradientButton } from "src/components/ui/gradient-button";
import { Skeleton } from "src/components/ui/skeleton";

const SOURCES = ["CRM", "KYC", "CBS", "RISK"] as const;
const RULES   = ["completeness","email_format","phone_format","dob_valid","name_quality","country_valid","no_test_data","kyc_consistency"] as const;

const MOCK: Record<string, { total: number; score: number; pass_rate: number }> = {
  CRM:  { total: 4500, score: 0.87, pass_rate: 0.94 },
  KYC:  { total: 3200, score: 0.94, pass_rate: 0.98 },
  CBS:  { total: 2300, score: 0.91, pass_rate: 0.96 },
  RISK: { total: 3000, score: 0.89, pass_rate: 0.95 },
};
const MOCK_RULES: Record<string, Record<string, number>> = {
  completeness:    { CRM: 94, KYC: 99, CBS: 96, RISK: 97 },
  email_format:    { CRM: 97, KYC: 99, CBS: 88, RISK: 85 },
  phone_format:    { CRM: 91, KYC: 95, CBS: 93, RISK: 90 },
  dob_valid:       { CRM: 99, KYC: 99, CBS: 98, RISK: 99 },
  name_quality:    { CRM: 96, KYC: 98, CBS: 97, RISK: 97 },
  country_valid:   { CRM: 99, KYC: 99, CBS: 99, RISK: 99 },
  no_test_data:    { CRM: 98, KYC: 99, CBS: 99, RISK: 99 },
  kyc_consistency: { CRM: 100, KYC: 96, CBS: 100, RISK: 100 },
};

const SRC_COLORS = ["#6366f1","#22c55e","#8b5cf6","#f59e0b"];

function cellBg(p: number) {
  if (p >= 95) return "bg-emerald-50 text-emerald-700 font-semibold";
  if (p >= 80) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700 font-semibold";
}

type Tab = "overview" | "rules" | "radar";

export default function DataQualityDashboard() {
  const [tab, setTab]   = useState<Tab>("overview");
  const [loading, setLoading] = useState(false);
  const [ts, setTs]     = useState(new Date());

  const barData = SOURCES.map((s) => ({ name: s, score: Math.round(MOCK[s].score * 100) }));
  const radarData = RULES.map((r) => ({
    rule: r.replace(/_/g, " "),
    avg: Math.round(SOURCES.map((s) => MOCK_RULES[r][s]).reduce((a, b) => a + b, 0) / 4),
  }));

  const refresh = async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    setTs(new Date());
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-slate-50">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Data Quality Monitor</h1>
          <p className="text-slate-500 text-sm mt-0.5">Last refresh: {ts.toLocaleTimeString()}</p>
        </div>
        <GradientButton variant="indigo" onClick={refresh} disabled={loading}>
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          {loading ? "Refreshing…" : "Refresh"}
        </GradientButton>
      </motion.div>

      {/* Source KPI cards */}
      <div className="grid grid-cols-4 gap-4">
        {SOURCES.map((src, i) => (
          <KpiCard
            key={src}
            label={`${src} Score`}
            value={Math.round(MOCK[src].score * 100)}
            suffix="%"
            color={(["indigo","green","purple","amber"] as const)[i]}
            delay={i * 0.08}
            description={`${MOCK[src].total.toLocaleString()} records`}
            icon={MOCK[src].score >= 0.9 ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            trend={Math.round((MOCK[src].score - 0.85) * 100)}
          />
        ))}
      </div>

      {/* Tabs */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
        className="flex gap-1 bg-white border border-slate-100 rounded-xl p-1 shadow-sm w-fit">
        {(["overview","rules","radar"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all ${
              tab === t ? "bg-indigo-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}>
            {t === "rules" ? "Rule Heatmap" : t === "radar" ? "Quality Radar" : "Bar Overview"}
          </button>
        ))}
      </motion.div>

      <AnimatePresence mode="wait">
        {tab === "overview" && (
          <motion.div key="overview"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">Average DQ Score by Source System</h2>
            {loading ? <Skeleton className="h-56 w-full" /> : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData} barSize={48}>
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} />
                  <YAxis domain={[80, 100]} unit="%" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <Tooltip formatter={(v) => [`${v}%`, "Score"]} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 13 }} />
                  <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                    {barData.map((_, i) => <Cell key={i} fill={SRC_COLORS[i]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </motion.div>
        )}

        {tab === "rules" && (
          <motion.div key="rules"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="text-left px-5 py-3">Rule</th>
                  {SOURCES.map((s) => <th key={s} className="px-4 py-3 font-semibold" style={{ color: SRC_COLORS[SOURCES.indexOf(s)] }}>{s}</th>)}
                  <th className="px-4 py-3">Overall</th>
                </tr>
              </thead>
              <tbody>
                {RULES.map((rule, ri) => {
                  const vals = SOURCES.map((s) => MOCK_RULES[rule][s]);
                  const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
                  return (
                    <motion.tr key={rule}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: ri * 0.04 }}
                      className="border-t border-slate-50 hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-3 font-medium text-slate-700 capitalize">{rule.replace(/_/g, " ")}</td>
                      {vals.map((v, i) => (
                        <td key={i} className={`px-4 py-3 text-center text-xs rounded-lg ${cellBg(v)}`}>{v}%</td>
                      ))}
                      <td className={`px-4 py-3 text-center text-xs font-bold ${cellBg(avg)}`}>{avg}%</td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </motion.div>
        )}

        {tab === "radar" && (
          <motion.div key="radar"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">Average Rule Quality — Radar View</h2>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="rule" tick={{ fontSize: 10, fill: "#64748b" }} />
                <Radar name="Avg %" dataKey="avg" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                <Tooltip formatter={(v) => [`${v}%`, "Score"]} />
              </RadarChart>
            </ResponsiveContainer>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
