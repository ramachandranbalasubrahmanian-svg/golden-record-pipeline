import { useEffect, useState, useCallback } from "react";
import { getQueue, stewardshipDecide, pairEvidence } from "../lib/api";
import { CheckCircle, XCircle, ChevronRight } from "lucide-react";

function probColor(p: number) {
  if (p >= 0.8) return "bg-green-500";
  if (p >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

function featureScore(score: number) {
  if (score > 0.8) return "bg-green-100 text-green-800";
  if (score >= 0.5) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

const MOCK_PAIRS = Array.from({ length: 20 }, (_, i) => ({
  pair_id: `pair-${i}`,
  record_a_id: `CRM-${100 + i}`,
  record_b_id: `KYC-${200 + i}`,
  source_a: "CRM",
  source_b: "KYC",
  match_probability: 0.65 + Math.random() * 0.34,
  match_features: {
    last_name_jaro_winkler: 0.92,
    dob_exact_match: 1.0,
    email_exact_match: i % 3 === 0 ? 1.0 : 0.0,
    phone_last6_match: 0.83,
    city_match: 1.0,
    source_system_different: 1.0,
    country_match: 1.0,
    first_name_soundex_match: 0.9,
  },
  status: "pending",
  record_a: { first_name: "John", last_name: "Smith", email: `j.smith${i}@crm.com`, date_of_birth: "1985-03-15", city: "New York" },
  record_b: { first_name: "JOHN", last_name: "SMITH", email: `jsmith${i}@kyc.com`, date_of_birth: "15/03/1985", city: "New York" },
}));

export default function StewardshipQueue() {
  const [pairs, setPairs] = useState<any[]>(MOCK_PAIRS);
  const [selected, setSelected] = useState<any>(MOCK_PAIRS[0]);
  const [notes, setNotes] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  const decide = async (decision: "approved" | "rejected") => {
    if (!selected) return;
    try {
      await stewardshipDecide(selected.pair_id, decision, notes);
    } catch (_) {}
    const remaining = pairs.filter((p) => p.pair_id !== selected.pair_id);
    setPairs(remaining);
    setSelected(remaining[0] ?? null);
    setNotes("");
    setToast(decision === "approved" ? "✓ Approved — Golden record updated" : "✗ Rejected — Records kept separate");
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "a") decide("approved");
      if (e.key === "r") decide("rejected");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected, notes, pairs]);

  return (
    <div className="flex h-full relative">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-800 text-white px-5 py-3 rounded-xl shadow-lg text-sm">
          {toast}
        </div>
      )}

      {/* Left queue */}
      <div className="w-80 border-r border-slate-200 bg-white overflow-y-auto">
        <div className="px-4 py-3 border-b border-slate-100">
          <p className="font-semibold text-slate-800">{pairs.length} pending</p>
          <p className="text-xs text-slate-500 mt-0.5">Sorted by probability ↓</p>
        </div>
        <div className="divide-y divide-slate-100">
          {[...pairs].sort((a, b) => b.match_probability - a.match_probability).map((pair) => (
            <button
              key={pair.pair_id}
              onClick={() => setSelected(pair)}
              className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${
                selected?.pair_id === pair.pair_id ? "bg-indigo-50 border-l-2 border-indigo-500" : ""
              }`}
            >
              <p className="text-sm font-medium text-slate-800">
                {pair.record_a?.first_name} {pair.record_a?.last_name}
              </p>
              <p className="text-xs text-slate-500">{pair.source_a} ↔ {pair.source_b}</p>
              <div className="mt-1.5 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className={`h-full rounded-full ${probColor(pair.match_probability)}`}
                  style={{ width: `${pair.match_probability * 100}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{(pair.match_probability * 100).toFixed(0)}% match</p>
            </button>
          ))}
        </div>
      </div>

      {/* Right detail */}
      {selected ? (
        <div className="flex-1 p-6 space-y-5 overflow-y-auto bg-slate-50">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800">
              Match Review — {selected.pair_id.slice(0, 8)}
            </h2>
            <div className={`text-2xl font-bold ${selected.match_probability >= 0.8 ? "text-green-600" : selected.match_probability >= 0.6 ? "text-amber-600" : "text-red-600"}`}>
              {(selected.match_probability * 100).toFixed(0)}%
            </div>
          </div>

          {/* Side-by-side comparison */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="text-left px-4 py-2.5 text-slate-600 font-medium">Attribute</th>
                  <th className="px-4 py-2.5 text-blue-600 font-medium">Record A ({selected.source_a})</th>
                  <th className="px-4 py-2.5 text-purple-600 font-medium">Record B ({selected.source_b})</th>
                  <th className="px-4 py-2.5 text-slate-600 font-medium text-center">Match</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {Object.keys(selected.record_a || {}).map((key) => {
                  const va = String(selected.record_a[key] ?? "—");
                  const vb = String(selected.record_b?.[key] ?? "—");
                  const match = va.toLowerCase() === vb.toLowerCase() || (key === "date_of_birth" && (va.replace(/\//g, "-") === vb || vb.replace(/\//g, "-") === va));
                  return (
                    <tr key={key}>
                      <td className="px-4 py-2.5 text-slate-600 capitalize">{key.replace(/_/g, " ")}</td>
                      <td className="px-4 py-2.5 text-center font-mono text-xs">{va}</td>
                      <td className="px-4 py-2.5 text-center font-mono text-xs">{vb}</td>
                      <td className="px-4 py-2.5 text-center">{match ? "✓" : "~"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Feature heatmap */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-sm font-semibold text-slate-700 mb-3">Feature Scores</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(selected.match_features || {}).map(([k, v]) => (
                <span key={k} className={`px-2.5 py-1 rounded text-xs font-medium ${featureScore(v as number)}`}>
                  {k.replace(/_/g, " ")}: {(v as number * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          </div>

          {/* Action bar */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3 sticky bottom-4">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reviewer notes (optional)"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <div className="flex gap-3">
              <button
                onClick={() => decide("approved")}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
              >
                <CheckCircle size={16} /> Approve Match (A)
              </button>
              <button
                onClick={() => decide("rejected")}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-red-500 text-red-600 rounded-lg hover:bg-red-50 font-medium"
              >
                <XCircle size={16} /> Reject — Different People (R)
              </button>
            </div>
            <p className="text-xs text-slate-400 text-center">Keyboard: A = approve · R = reject · J/K = navigate</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-400">
          <p>All pairs reviewed!</p>
        </div>
      )}
    </div>
  );
}
