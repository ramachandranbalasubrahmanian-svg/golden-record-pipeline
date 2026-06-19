import { useEffect, useState } from "react";
import { sourceWins, activeConflicts } from "../lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Lock, AlertCircle } from "lucide-react";

const MOCK_WINS = {
  KYC:  { total_attributes: 4200, pct: 0.48, attributes: ["kyc_status", "kyc_tier", "nationality", "is_pep", "is_sanctioned", "id_number"] },
  CBS:  { total_attributes: 2100, pct: 0.24, attributes: ["date_of_birth", "address_line1", "city", "postcode"] },
  RISK: { total_attributes: 1400, pct: 0.16, attributes: ["risk_rating", "risk_score", "aml_flag", "fraud_flag"] },
  CRM:  { total_attributes: 1050, pct: 0.12, attributes: ["email", "phone", "first_name", "last_name", "country"] },
};

const MOCK_CONFLICTS = [
  { customer_id: "cust-0042", attribute_name: "phone", kyc_value: "+447911123456", crm_value: "(555) 123-4567", resolved_by: "KYC wins (trust 1.00)", is_regulatory_lock: false },
  { customer_id: "cust-0117", attribute_name: "date_of_birth", kyc_value: "1978-05-22", cbs_value: "22/05/1978", resolved_by: "KYC wins (trust 1.00)", is_regulatory_lock: false },
  { customer_id: "cust-0238", attribute_name: "is_pep", kyc_value: "true", crm_value: "false", resolved_by: "REGULATORY LOCK → KYC", is_regulatory_lock: true },
  { customer_id: "cust-0391", attribute_name: "address_line1", kyc_value: "123 HIGH STREET", cbs_value: "123 High Street, Flat 4", resolved_by: "CBS wins (recency 0.95)", is_regulatory_lock: false },
  { customer_id: "cust-0512", attribute_name: "risk_rating", risk_value: "CRITICAL", cbs_value: "HIGH", resolved_by: "RISK wins (trust 0.90)", is_regulatory_lock: false },
];

const ATTR_GROUPS = [
  { group: "Identity (Regulatory Lock)", attrs: ["kyc_status", "kyc_tier", "is_pep", "is_sanctioned", "pep_type", "sanctions_list"], lock: true },
  { group: "Personal Details", attrs: ["first_name", "last_name", "date_of_birth", "nationality", "gender"], lock: false },
  { group: "Contact", attrs: ["email", "phone", "address_line1", "city", "postcode", "country"], lock: false },
  { group: "Risk Profile", attrs: ["risk_rating", "risk_score", "aml_flag", "fraud_flag"], lock: false },
];

const SOURCE_COLORS: Record<string, string> = {
  KYC: "#6366f1", CBS: "#8b5cf6", RISK: "#f59e0b", CRM: "#22c55e",
};

export default function LineageVisualizer() {
  const [wins, setWins] = useState<any>(null);
  const [conflicts, setConflicts] = useState<any[]>(MOCK_CONFLICTS);
  const [customerId, setCustomerId] = useState("");
  const [tab, setTab] = useState<"flow" | "wins" | "conflicts">("flow");

  useEffect(() => {
    sourceWins().then(setWins).catch(() => setWins(MOCK_WINS));
    activeConflicts().then((d: any) => setConflicts(d.conflicts ?? MOCK_CONFLICTS)).catch(() => setConflicts(MOCK_CONFLICTS));
  }, []);

  const displayWins = wins ?? MOCK_WINS;
  const barData = Object.entries(displayWins).map(([src, data]: any) => ({
    name: src,
    wins: data.total_attributes,
    pct: Math.round(data.pct * 100),
  }));

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Lineage Visualizer</h1>
        <div className="flex items-center gap-3">
          <input
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Filter by Customer ID"
            className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Filter</button>
        </div>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {(["flow", "wins", "conflicts"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t ? "border-b-2 border-indigo-600 text-indigo-600" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t === "flow" ? "Lineage Flow" : t === "wins" ? "Source Wins" : "Active Conflicts"}
          </button>
        ))}
      </div>

      {tab === "flow" && (
        <div className="space-y-4">
          <p className="text-slate-500 text-sm">
            Showing how attributes flow from source systems into the Golden Record. Regulatory Lock attributes
            always come from KYC (overrides survivorship scoring).
          </p>

          {/* Pipeline flow diagram */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6">
            <div className="flex items-start gap-4">
              {/* Source boxes */}
              <div className="flex flex-col gap-3 w-32">
                {Object.keys(MOCK_WINS).map((src) => (
                  <div key={src} className="rounded-lg px-3 py-2 text-center text-sm font-bold text-white" style={{ backgroundColor: SOURCE_COLORS[src] }}>
                    {src}
                  </div>
                ))}
              </div>

              {/* Arrows */}
              <div className="flex flex-col justify-around h-full gap-3 pt-1">
                {Object.keys(MOCK_WINS).map((src) => (
                  <div key={src} className="flex items-center">
                    <div className="w-16 h-0.5" style={{ backgroundColor: SOURCE_COLORS[src] }} />
                    <div className="w-2 h-2 rotate-45 -ml-1.5" style={{ backgroundColor: SOURCE_COLORS[src] }} />
                  </div>
                ))}
              </div>

              {/* Survivorship engine */}
              <div className="flex-1 rounded-xl bg-slate-800 text-white p-4">
                <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">Survivorship Engine</p>
                <div className="space-y-1.5 text-xs text-slate-400">
                  <p>trust_weight × 0.50</p>
                  <p>recency_score × 0.30</p>
                  <p>completeness × 0.20</p>
                  <div className="mt-2 pt-2 border-t border-slate-700">
                    <p className="text-amber-400 flex items-center gap-1"><Lock size={10} /> REGULATORY LOCK: KYC/PEP/Sanctions always from KYC</p>
                  </div>
                </div>
              </div>

              {/* Arrow out */}
              <div className="flex items-center pt-1">
                <div className="w-10 h-0.5 bg-slate-400" />
                <div className="w-2 h-2 rotate-45 -ml-1.5 bg-slate-400" />
              </div>

              {/* Golden record */}
              <div className="rounded-xl bg-indigo-600 text-white px-4 py-3 w-32 text-center">
                <p className="text-xs text-indigo-200 mb-1">Output</p>
                <p className="text-sm font-bold">Golden Record</p>
              </div>
            </div>
          </div>

          {/* Attribute groups */}
          <div className="grid grid-cols-2 gap-4">
            {ATTR_GROUPS.map((group) => (
              <div key={group.group} className={`bg-white rounded-xl border shadow-sm p-4 ${group.lock ? "border-amber-300" : "border-slate-100"}`}>
                <div className="flex items-center gap-2 mb-3">
                  {group.lock && <Lock size={14} className="text-amber-500" />}
                  <p className="text-sm font-semibold text-slate-700">{group.group}</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {group.attrs.map((attr) => (
                    <span key={attr} className={`text-xs px-2 py-0.5 rounded ${group.lock ? "bg-amber-50 text-amber-800" : "bg-slate-50 text-slate-700"}`}>
                      {attr}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "wins" && (
        <div className="space-y-5">
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(displayWins).map(([src, data]: any) => (
              <div key={src} className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: SOURCE_COLORS[src] }} />
                  <p className="font-bold text-slate-800">{src}</p>
                </div>
                <p className="text-2xl font-bold text-slate-800">{(data.pct * 100).toFixed(0)}%</p>
                <p className="text-slate-500 text-xs">{data.total_attributes.toLocaleString()} attributes</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {data.attributes?.slice(0, 3).map((a: string) => (
                    <span key={a} className="text-xs px-1.5 py-0.5 bg-slate-50 rounded text-slate-600">{a}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">Attribute Wins by Source</h2>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(v, n) => [v, n === "wins" ? "Attributes Won" : "Share %"]} />
                <Bar dataKey="wins" radius={[4, 4, 0, 0]}>
                  {barData.map((d, i) => <Cell key={i} fill={SOURCE_COLORS[d.name]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === "conflicts" && (
        <div className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Customer</th>
                <th className="text-left px-4 py-3">Attribute</th>
                <th className="px-4 py-3">Source A</th>
                <th className="px-4 py-3">Source B</th>
                <th className="text-left px-4 py-3">Resolution</th>
                <th className="px-4 py-3">Lock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {conflicts.map((c, i) => (
                <tr key={i} className={`hover:bg-slate-50 ${c.is_regulatory_lock ? "bg-amber-50" : ""}`}>
                  <td className="px-4 py-3 font-mono text-xs text-indigo-600">{c.customer_id}</td>
                  <td className="px-4 py-3 font-medium text-slate-700">{c.attribute_name}</td>
                  <td className="px-4 py-3 text-center font-mono text-xs text-slate-600">{c.kyc_value ?? c.risk_value}</td>
                  <td className="px-4 py-3 text-center font-mono text-xs text-slate-600">{c.crm_value ?? c.cbs_value}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{c.resolved_by}</td>
                  <td className="px-4 py-3 text-center">
                    {c.is_regulatory_lock && <Lock size={14} className="text-amber-500 mx-auto" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
