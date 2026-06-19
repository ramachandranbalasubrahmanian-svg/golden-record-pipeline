import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { stewardshipDecide } from "../lib/api";
import { CheckCircle2, XCircle, ChevronRight, Zap } from "lucide-react";
import { GradientButton } from "src/components/ui/gradient-button";
import { Progress } from "src/components/ui/progress";
import { Skeleton } from "src/components/ui/skeleton";

function probBar(p: number) {
  if (p >= 0.85) return "bg-gradient-to-r from-emerald-400 to-green-500";
  if (p >= 0.65) return "bg-gradient-to-r from-amber-400 to-orange-500";
  return "bg-gradient-to-r from-red-400 to-rose-500";
}
function probText(p: number) {
  if (p >= 0.85) return "text-emerald-600";
  if (p >= 0.65) return "text-amber-600";
  return "text-red-600";
}
function featureChip(v: number) {
  if (v > 0.8) return "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (v >= 0.5) return "bg-amber-100 text-amber-800 border-amber-200";
  return "bg-red-100 text-red-800 border-red-200";
}

const MOCK_PAIRS = Array.from({ length: 20 }, (_, i) => ({
  pair_id: `pair-${i}`,
  source_a: "CRM", source_b: "KYC",
  match_probability: 0.55 + (((i * 13) % 40) / 100),
  match_features: {
    last_name_jaro_winkler: 0.92, dob_exact_match: 1.0,
    email_exact_match: i % 3 === 0 ? 1.0 : 0.0,
    phone_last6_match: 0.83, city_match: 1.0,
    country_match: 1.0, first_name_soundex: 0.9,
  },
  record_a: { first_name: "John", last_name: "Smith", email: `j.smith${i}@crm.com`, date_of_birth: "1985-03-15", city: "New York" },
  record_b: { first_name: "JOHN", last_name: "SMITH", email: `jsmith${i}@kyc.com`, date_of_birth: "15/03/1985", city: "New York" },
}));

export default function StewardshipQueue() {
  const [pairs, setPairs] = useState(MOCK_PAIRS);
  const [selected, setSelected] = useState(MOCK_PAIRS[0]);
  const [notes, setNotes] = useState("");
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [deciding, setDeciding] = useState(false);

  const decide = async (decision: "approved" | "rejected") => {
    if (!selected || deciding) return;
    setDeciding(true);
    try { await stewardshipDecide(selected.pair_id, decision, notes); } catch (_) {}
    const remaining = pairs.filter((p) => p.pair_id !== selected.pair_id);
    setPairs(remaining);
    setSelected(remaining[0] ?? null!);
    setNotes("");
    setToast({ msg: decision === "approved" ? "Match approved — golden record merged" : "Rejected — records kept separate", ok: decision === "approved" });
    setTimeout(() => setToast(null), 3000);
    setDeciding(false);
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "a") decide("approved");
      if (e.key === "r") decide("rejected");
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  });

  const sortedPairs = [...pairs].sort((a, b) => b.match_probability - a.match_probability);

  return (
    <div className="flex h-full relative overflow-hidden">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9 }}
            className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5 px-5 py-3 rounded-xl shadow-xl text-white text-sm font-medium ${toast.ok ? "bg-emerald-600" : "bg-slate-700"}`}
          >
            {toast.ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Queue list */}
      <div className="w-72 border-r border-slate-200 bg-white flex flex-col shrink-0">
        <div className="px-4 py-4 border-b border-slate-100 bg-slate-50">
          <p className="font-bold text-slate-800">{pairs.length} pending</p>
          <p className="text-xs text-slate-500 mt-0.5">Sorted by confidence ↓</p>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
          {sortedPairs.map((pair) => (
            <motion.button
              key={pair.pair_id}
              onClick={() => setSelected(pair)}
              whileHover={{ x: 2 }}
              className={`w-full text-left px-4 py-3.5 transition-colors hover:bg-slate-50 ${selected?.pair_id === pair.pair_id ? "bg-indigo-50 border-l-2 border-indigo-500" : ""}`}
            >
              <p className="text-sm font-semibold text-slate-800">
                {pair.record_a.first_name} {pair.record_a.last_name}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{pair.source_a} ↔ {pair.source_b}</p>
              <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pair.match_probability * 100}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  className={`h-full rounded-full ${probBar(pair.match_probability)}`}
                />
              </div>
              <p className={`text-xs font-bold mt-1 ${probText(pair.match_probability)}`}>
                {(pair.match_probability * 100).toFixed(0)}% match
              </p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Detail */}
      {selected ? (
        <motion.div
          key={selected.pair_id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25 }}
          className="flex-1 bg-slate-50 overflow-y-auto flex flex-col"
        >
          <div className="p-6 space-y-5 flex-1">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Match Review</h2>
                <p className="text-slate-500 text-sm font-mono">{selected.pair_id}</p>
              </div>
              <div className={`text-3xl font-black tabular-nums ${probText(selected.match_probability)}`}>
                {(selected.match_probability * 100).toFixed(0)}%
              </div>
            </div>

            {/* Side-by-side */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
              <div className="grid grid-cols-3 bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                <div className="px-4 py-3">Attribute</div>
                <div className="px-4 py-3 text-blue-600">{selected.source_a}</div>
                <div className="px-4 py-3 text-purple-600">{selected.source_b}</div>
              </div>
              <div className="divide-y divide-slate-50">
                {Object.entries(selected.record_a).map(([k, va]) => {
                  const vb = (selected.record_b as any)[k] ?? "—";
                  const match = String(va).toLowerCase() === String(vb).toLowerCase();
                  return (
                    <div key={k} className={`grid grid-cols-3 text-sm ${match ? "" : "bg-amber-50/40"}`}>
                      <div className="px-4 py-2.5 text-slate-500 capitalize font-medium">{k.replace(/_/g, " ")}</div>
                      <div className="px-4 py-2.5 font-mono text-xs text-slate-700">{String(va)}</div>
                      <div className="px-4 py-2.5 font-mono text-xs text-slate-700">
                        {String(vb)}
                        {!match && <span className="ml-2 text-amber-500">≠</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Feature chips */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
              <p className="text-sm font-semibold text-slate-700 mb-3">ML Feature Scores</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(selected.match_features).map(([k, v]) => (
                  <motion.span
                    key={k}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${featureChip(v as number)}`}
                  >
                    {k.replace(/_/g, " ")}: {((v as number) * 100).toFixed(0)}%
                  </motion.span>
                ))}
              </div>
            </div>
          </div>

          {/* Action bar */}
          <div className="sticky bottom-0 bg-white border-t border-slate-100 px-6 py-4 space-y-3">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reviewer notes (optional)…"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-slate-50"
            />
            <div className="flex gap-3">
              <GradientButton variant="green" size="md" onClick={() => decide("approved")} disabled={deciding} className="flex-1 justify-center">
                <CheckCircle2 size={15} /> Approve (A)
              </GradientButton>
              <motion.button
                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                onClick={() => decide("rejected")}
                disabled={deciding}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border-2 border-red-300 text-red-600 rounded-lg text-sm font-semibold hover:bg-red-50 transition-colors disabled:opacity-50"
              >
                <XCircle size={15} /> Reject (R)
              </motion.button>
            </div>
            <p className="text-center text-xs text-slate-400">A = approve · R = reject</p>
          </div>
        </motion.div>
      ) : (
        <div className="flex-1 flex items-center justify-center bg-slate-50">
          <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center">
            <CheckCircle2 size={48} className="text-emerald-400 mx-auto mb-3" />
            <p className="text-slate-600 font-semibold">All pairs reviewed!</p>
            <p className="text-slate-400 text-sm mt-1">Queue is empty</p>
          </motion.div>
        </div>
      )}
    </div>
  );
}
