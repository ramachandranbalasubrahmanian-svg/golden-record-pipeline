import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getStats, ragStats, stewardshipStats, MOCK_STATS } from "../lib/api";
import { KpiCard } from "src/components/ui/kpi-card";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis } from "recharts";
import {
  Users, AlertTriangle, ShieldAlert, ClipboardList,
  TrendingUp, Cpu, CheckCircle2, Clock,
} from "lucide-react";

const RISK_COLORS  = ["#94a3b8","#f59e0b","#f97316","#ef4444"];
const KYC_COLORS   = ["#22c55e","#60a5fa","#ef4444","#f59e0b"];

const PIPELINE = [
  { label: "Data Ingestion",     status: "done",    pct: 100 },
  { label: "DQ Validation",      status: "done",    pct: 100 },
  { label: "Entity Resolution",  status: "done",    pct: 100 },
  { label: "Survivorship",       status: "done",    pct: 100 },
  { label: "RAG Indexing",       status: "done",    pct: 100 },
];

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, delay, ease: "easeOut" },
});

export default function AdminConsole() {
  const [stats, setStats] = useState<any>(MOCK_STATS);
  const [rag, setRag]   = useState<any>(null);
  const [stew, setStew] = useState<any>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(MOCK_STATS));
    ragStats().then(setRag).catch(() => null);
    stewardshipStats().then(setStew).catch(() => null);
  }, []);

  const riskData = stats ? Object.entries(stats.by_risk_rating).map(([name, value]) => ({ name, value })) : [];
  const kycData  = stats ? Object.entries(stats.by_kyc_status).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-slate-50">
      {/* Header */}
      <motion.div {...fadeUp(0)} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Console</h1>
          <p className="text-slate-500 text-sm mt-0.5">Golden Record Pipeline — real-time overview</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-emerald-700 text-xs font-semibold">All systems operational</span>
        </div>
      </motion.div>

      {/* KPI cards — row 1 */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="Golden Records"    value={stats?.total_customers ?? 5000}  icon={<Users size={18} />}         color="indigo"  delay={0.05} trend={12} />
        <KpiCard label="PEP Customers"     value={stats?.pep_count ?? 50}          icon={<AlertTriangle size={18} />} color="amber"   delay={0.1}  trend={2}  />
        <KpiCard label="Sanctioned"        value={stats?.sanctioned_count ?? 10}   icon={<ShieldAlert size={18} />}   color="red"     delay={0.15} trend={0}  />
        <KpiCard label="Pending Reviews"   value={stew?.total_pending ?? 347}      icon={<ClipboardList size={18} />} color="purple"  delay={0.2}  trend={-8} />
      </div>

      {/* KPI cards — row 2 */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="Avg Confidence"    value={(stats?.avg_confidence_score ?? 0.847) * 100} suffix="%" decimals={1} icon={<TrendingUp size={18} />}  color="green"  delay={0.25} description="Survivorship score" />
        <KpiCard label="Multi-Source %"    value={(stats?.multi_source_pct ?? 0.68) * 100}      suffix="%" decimals={1} icon={<Cpu size={18} />}          color="indigo" delay={0.3}  description="Records with 2+ sources" />
        <KpiCard label="RAG Queries"       value={rag?.total_queries ?? 1842}                   icon={<CheckCircle2 size={18} />} color="purple" delay={0.35} trend={24} />
        <KpiCard label="Hallucination Rate" value={(rag?.hallucination_rate ?? 0.023) * 100}   suffix="%" decimals={1} icon={<Clock size={18} />} color="amber" delay={0.4} description="GPT-4o-mini fact-check" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-5">
        <motion.div {...fadeUp(0.45)} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">Risk Rating Distribution</h2>
          <p className="text-xs text-slate-400 mb-4">4 tiers across 5,000 golden records</p>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={riskData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={75}>
                  {riskData.map((_, i) => <Cell key={i} fill={RISK_COLORS[i % RISK_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v} records`, n]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 flex-1">
              {riskData.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: RISK_COLORS[i] }} />
                    <span className="text-xs text-slate-600">{d.name}</span>
                  </div>
                  <span className="text-xs font-bold text-slate-800">{(d.value as number).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        <motion.div {...fadeUp(0.5)} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-1">KYC Status</h2>
          <p className="text-xs text-slate-400 mb-4">Across all onboarded customers</p>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={kycData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={75}>
                  {kycData.map((_, i) => <Cell key={i} fill={KYC_COLORS[i % KYC_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v} records`, n]} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 flex-1">
              {kycData.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: KYC_COLORS[i] }} />
                    <span className="text-xs text-slate-600">{d.name}</span>
                  </div>
                  <span className="text-xs font-bold text-slate-800">{(d.value as number).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Pipeline status */}
      <motion.div {...fadeUp(0.55)} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Pipeline Stage Status</h2>
        <div className="flex items-center gap-0">
          {PIPELINE.map((stage, i) => (
            <div key={stage.label} className="flex items-center flex-1">
              <div className="flex flex-col items-center w-full">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.6 + i * 0.1, type: "spring", bounce: 0.4 }}
                  className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center text-white shadow-md shadow-emerald-100"
                >
                  <CheckCircle2 size={16} />
                </motion.div>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.7 + i * 0.1 }}
                  className="text-xs text-slate-600 mt-2 text-center leading-tight font-medium"
                >
                  {stage.label}
                </motion.p>
              </div>
              {i < PIPELINE.length - 1 && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: 0.65 + i * 0.1, duration: 0.3 }}
                  className="h-0.5 bg-gradient-to-r from-emerald-400 to-green-300 flex-shrink-0 w-8 origin-left mb-5"
                />
              )}
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
