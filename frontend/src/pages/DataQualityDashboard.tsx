import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { RefreshCw } from "lucide-react";

const SOURCES = ["CRM", "KYC", "CBS", "RISK"];
const RULES = [
  "completeness", "email_format", "phone_format", "dob_valid",
  "name_quality", "country_valid", "no_test_data", "kyc_consistency",
];

const MOCK = {
  CRM:  { total: 4500, score: 0.87, pass_rate: 0.94 },
  KYC:  { total: 3200, score: 0.94, pass_rate: 0.98 },
  CBS:  { total: 2300, score: 0.91, pass_rate: 0.96 },
  RISK: { total: 3000, score: 0.89, pass_rate: 0.95 },
};
const MOCK_RULES: Record<string, Record<string, number>> = {
  completeness:  { CRM: 94, KYC: 99, CBS: 96, RISK: 97 },
  email_format:  { CRM: 97, KYC: 99, CBS: 88, RISK: 85 },
  phone_format:  { CRM: 91, KYC: 95, CBS: 93, RISK: 90 },
  dob_valid:     { CRM: 99, KYC: 99, CBS: 98, RISK: 99 },
  name_quality:  { CRM: 96, KYC: 98, CBS: 97, RISK: 97 },
  country_valid: { CRM: 99, KYC: 99, CBS: 99, RISK: 99 },
  no_test_data:  { CRM: 98, KYC: 99, CBS: 99, RISK: 99 },
  kyc_consistency: { CRM: 100, KYC: 96, CBS: 100, RISK: 100 },
};

function scoreColor(score: number) {
  if (score >= 0.85) return "text-green-600";
  if (score >= 0.70) return "text-amber-600";
  return "text-red-600";
}

function cellColor(pct: number) {
  if (pct >= 95) return "bg-green-50 text-green-800";
  if (pct >= 80) return "bg-amber-50 text-amber-800";
  return "bg-red-50 text-red-800";
}

type Tab = "overview" | "rules" | "failed";

export default function DataQualityDashboard() {
  const [tab, setTab] = useState<Tab>("overview");
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const barData = SOURCES.map((s) => ({
    name: s,
    score: Math.round(MOCK[s as keyof typeof MOCK].score * 100),
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Data Quality Monitor</h1>
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span>Last refresh: {lastRefresh.toLocaleTimeString()}</span>
          <button
            onClick={() => setLastRefresh(new Date())}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Source cards */}
      <div className="grid grid-cols-4 gap-4">
        {SOURCES.map((src) => {
          const d = MOCK[src as keyof typeof MOCK];
          return (
            <div key={src} className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
              <p className="text-slate-500 text-xs font-semibold uppercase tracking-wide">{src}</p>
              <p className={`text-3xl font-bold mt-2 ${scoreColor(d.score)}`}>
                {(d.score * 100).toFixed(0)}%
              </p>
              <p className="text-slate-500 text-xs mt-1">{d.total.toLocaleString()} records</p>
              <p className="text-slate-500 text-xs">Pass rate: {(d.pass_rate * 100).toFixed(0)}%</p>
            </div>
          );
        })}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {(["overview", "rules", "failed"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? "border-b-2 border-indigo-600 text-indigo-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "failed" ? "Failed Records" : t === "rules" ? "Rule Breakdown" : "Overview"}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <h2 className="text-base font-semibold text-slate-700 mb-4">Average DQ Score by Source</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={barData}>
              <XAxis dataKey="name" />
              <YAxis domain={[80, 100]} unit="%" />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                {barData.map((_, i) => (
                  <Cell key={i} fill={["#6366f1", "#22c55e", "#8b5cf6", "#f59e0b"][i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {tab === "rules" && (
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Rule</th>
                {SOURCES.map((s) => <th key={s} className="px-4 py-3">{s}</th>)}
                <th className="px-4 py-3">Overall</th>
              </tr>
            </thead>
            <tbody>
              {RULES.map((rule) => {
                const vals = SOURCES.map((s) => MOCK_RULES[rule][s]);
                const avg = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);
                return (
                  <tr key={rule} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-700">{rule.replace(/_/g, " ")}</td>
                    {vals.map((v, i) => (
                      <td key={i} className={`px-4 py-3 text-center font-mono ${cellColor(v)}`}>{v}%</td>
                    ))}
                    <td className={`px-4 py-3 text-center font-mono font-bold ${cellColor(avg)}`}>{avg}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === "failed" && (
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
          <p className="text-slate-500 text-sm">
            Connect to a live API to see failed records. With mock data, ~5% of records
            score below 0.60 threshold and are quarantined before the pipeline runs.
          </p>
        </div>
      )}
    </div>
  );
}
