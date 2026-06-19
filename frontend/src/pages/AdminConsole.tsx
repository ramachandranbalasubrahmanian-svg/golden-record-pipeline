import { useEffect, useState } from "react";
import { getStats, ragStats, stewardshipStats, MOCK_STATS } from "../lib/api";
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis,
  Tooltip, ResponsiveContainer, LineChart, Line,
} from "recharts";

const RISK_COLORS = ["#94a3b8", "#fbbf24", "#f97316", "#ef4444"];
const KYC_COLORS = ["#22c55e", "#60a5fa", "#ef4444", "#fbbf24"];

export default function AdminConsole() {
  const [stats, setStats] = useState<any>(MOCK_STATS);
  const [rag, setRag] = useState<any>(null);
  const [stew, setStew] = useState<any>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(MOCK_STATS));
    ragStats().then(setRag).catch(() => null);
    stewardshipStats().then(setStew).catch(() => null);
  }, []);

  const riskData = stats
    ? Object.entries(stats.by_risk_rating).map(([name, value]) => ({ name, value }))
    : [];
  const kycData = stats
    ? Object.entries(stats.by_kyc_status).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Admin Console</h1>

      {/* Top metric cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Golden Records", value: stats?.total_customers?.toLocaleString() ?? "—", color: "indigo" },
          { label: "PEP Customers", value: stats?.pep_count ?? "—", color: "amber" },
          { label: "Sanctioned", value: stats?.sanctioned_count ?? "—", color: "red" },
          { label: "Pending Reviews", value: stew?.total_pending ?? "—", color: "purple" },
        ].map((c) => (
          <div key={c.label} className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
            <p className="text-slate-500 text-sm">{c.label}</p>
            <p className="text-3xl font-bold text-slate-800 mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      {/* Second row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Avg Confidence", value: stats ? `${(stats.avg_confidence_score * 100).toFixed(1)}%` : "—" },
          { label: "Multi-Source %", value: stats ? `${(stats.multi_source_pct * 100).toFixed(1)}%` : "—" },
          { label: "Total Queries", value: rag?.total_queries?.toLocaleString() ?? "—" },
          { label: "Hallucination Rate", value: rag ? `${(rag.hallucination_rate * 100).toFixed(1)}%` : "—" },
        ].map((c) => (
          <div key={c.label} className="bg-white rounded-xl shadow-sm border border-slate-100 p-5">
            <p className="text-slate-500 text-sm">{c.label}</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <h2 className="text-base font-semibold text-slate-700 mb-4">Risk Rating Distribution</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}`}>
                {riskData.map((_, i) => <Cell key={i} fill={RISK_COLORS[i % RISK_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <h2 className="text-base font-semibold text-slate-700 mb-4">KYC Status Distribution</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={kycData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}`}>
                {kycData.map((_, i) => <Cell key={i} fill={KYC_COLORS[i % KYC_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Pipeline health */}
      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
        <h2 className="text-base font-semibold text-slate-700 mb-4">Pipeline Stage Status</h2>
        <div className="flex items-center gap-0">
          {["Data Ingestion", "DQ Validation", "Entity Resolution", "Survivorship", "RAG Indexing"].map((stage, i, arr) => (
            <div key={stage} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-bold">✓</div>
                <p className="text-xs text-slate-600 mt-1 text-center w-20">{stage}</p>
              </div>
              {i < arr.length - 1 && <div className="w-12 h-0.5 bg-green-300 mb-5" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
