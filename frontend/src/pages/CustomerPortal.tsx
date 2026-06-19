import { useEffect, useState } from "react";
import { getCustomerFull, ragQuery, submitErasure } from "../lib/api";
import { User, FileText, MessageSquare, Trash2, Lock, Eye, EyeOff } from "lucide-react";

const DEMO_CUSTOMER_ID = "cust-0001";

export default function CustomerPortal() {
  const [customerId, setCustomerId] = useState(DEMO_CUSTOMER_ID);
  const [inputId, setInputId] = useState(DEMO_CUSTOMER_ID);
  const [profile, setProfile] = useState<any>(null);
  const [tab, setTab] = useState<"profile" | "chat" | "privacy">("profile");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [erasureState, setErasureState] = useState<"idle" | "confirm" | "submitted">("idle");
  const [erasureReason, setErasureReason] = useState("");
  const [showRawData, setShowRawData] = useState(false);

  const MOCK_PROFILE = {
    full_legal_name: "Alice Smith",
    email: "alice.smith@example.com",
    phone: "+1 555 0101",
    date_of_birth: "1985-03-15",
    address_line1: "123 Main Street",
    city: "New York",
    country: "United States",
    kyc_status: "VERIFIED",
    kyc_expiry_at: "2026-08-01",
    source_count: 3,
  };

  useEffect(() => {
    getCustomerFull(customerId)
      .then(setProfile)
      .catch(() => setProfile(MOCK_PROFILE));
  }, [customerId]);

  const send = async () => {
    if (!chatInput.trim() || loading) return;
    const q = chatInput;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setChatInput("");
    setLoading(true);
    try {
      const res: any = await ragQuery({ question: q, entity_id: customerId, persona: "customer" });
      setMessages((m) => [...m, { role: "assistant", content: res.answer ?? "I could not find information about that." }]);
    } catch (_) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content:
            "I'm having trouble connecting to the service right now. " +
            "This portal uses the customer persona — risk and PEP data are not exposed.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const submitRight = async () => {
    try {
      await submitErasure(customerId, "customer@example.com", erasureReason || "Customer GDPR erasure request");
    } catch (_) {}
    setErasureState("submitted");
  };

  const p = profile ?? MOCK_PROFILE;

  return (
    <div className="min-h-full bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-lg font-bold text-slate-800">My Profile</p>
            <p className="text-slate-400 text-xs">Secure Customer Portal</p>
          </div>
          <div className="flex items-center gap-3">
            <input
              value={inputId}
              onChange={(e) => setInputId(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none"
              placeholder="Customer ID"
            />
            <button
              onClick={() => setCustomerId(inputId)}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              Load
            </button>
          </div>
        </div>
      </div>

      {/* Notice banner */}
      <div className="bg-blue-600 text-white px-6 py-2 text-center text-sm">
        <Lock size={12} className="inline mr-1" />
        This portal uses the Customer persona — sensitive compliance and risk data is not displayed.
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Welcome card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
              <User size={28} className="text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">{p.full_legal_name ?? "—"}</h1>
              <p className="text-slate-500 text-sm">{p.email}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${p.kyc_status === "VERIFIED" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
                  {p.kyc_status ?? "—"}
                </span>
                {p.kyc_expiry_at && (
                  <span className="text-xs text-slate-400">Expires {new Date(p.kyc_expiry_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-xl border border-slate-100 p-1 shadow-sm">
          {([
            { id: "profile", label: "My Details", icon: FileText },
            { id: "chat", label: "Ask About My Data", icon: MessageSquare },
            { id: "privacy", label: "Privacy Rights", icon: Trash2 },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                tab === id ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {tab === "profile" && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-base font-semibold text-slate-800">Your Information</h2>
              <button
                onClick={() => setShowRawData(!showRawData)}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700"
              >
                {showRawData ? <EyeOff size={12} /> : <Eye size={12} />}
                {showRawData ? "Hide" : "Show"} raw values
              </button>
            </div>
            <div className="space-y-3">
              {[
                ["Full Name", p.full_legal_name],
                ["Email", p.email],
                ["Phone", p.phone],
                ["Date of Birth", p.date_of_birth ? new Date(p.date_of_birth).toLocaleDateString() : "—"],
                ["Address", [p.address_line1, p.city].filter(Boolean).join(", ")],
                ["Country", p.country],
                ["KYC Status", p.kyc_status],
                ["KYC Expiry", p.kyc_expiry_at ? new Date(p.kyc_expiry_at).toLocaleDateString() : "—"],
                ["Data Sources", `${p.source_count ?? "?"} verified systems`],
              ].map(([label, value]) => (
                <div key={String(label)} className="flex justify-between py-2 border-b border-slate-50 last:border-0">
                  <span className="text-slate-500 text-sm">{label}</span>
                  <span className="text-slate-800 text-sm font-medium">{String(value ?? "—")}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-xs text-blue-700">
                Your data is compiled from {p.source_count ?? "multiple"} verified sources using our Golden Record process.
                Risk and compliance data is not shown here.
              </p>
            </div>
          </div>
        )}

        {tab === "chat" && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="h-72 overflow-y-auto p-4 space-y-3 bg-slate-50">
              {messages.length === 0 && (
                <div className="text-center text-slate-400 mt-8">
                  <MessageSquare size={32} className="mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Ask questions about your data</p>
                  <div className="mt-3 space-y-1">
                    {["What data do you hold about me?", "What is my KYC status?"].map((q) => (
                      <button key={q} onClick={() => setChatInput(q)} className="block w-full text-xs text-left px-3 py-1.5 bg-white rounded-lg text-slate-600 hover:bg-blue-50 border border-slate-100">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-xs rounded-xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-blue-600 text-white" : "bg-white border border-slate-200 text-slate-800"}`}>
                    {m.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-slate-100 flex gap-3">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Ask about your data…"
                className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button onClick={send} disabled={!chatInput.trim() || loading} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700">
                Send
              </button>
            </div>
          </div>
        )}

        {tab === "privacy" && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 space-y-5">
            <h2 className="text-base font-semibold text-slate-800">Your Privacy Rights (GDPR)</h2>

            <div className="space-y-3">
              {[
                { right: "Right to Access", desc: "Download all data we hold about you as JSON", action: "Download My Data" },
                { right: "Right to Rectification", desc: "Request correction of inaccurate data", action: "Request Correction" },
              ].map((r) => (
                <div key={r.right} className="flex justify-between items-center p-4 bg-slate-50 rounded-xl">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">{r.right}</p>
                    <p className="text-slate-500 text-xs">{r.desc}</p>
                  </div>
                  <button className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-white">
                    {r.action}
                  </button>
                </div>
              ))}

              <div className="p-4 bg-red-50 rounded-xl border border-red-100">
                <p className="font-medium text-red-800 text-sm">Right to Erasure</p>
                <p className="text-red-600 text-xs mt-0.5">Request deletion of all your data (Article 17 GDPR)</p>

                {erasureState === "idle" && (
                  <button
                    onClick={() => setErasureState("confirm")}
                    className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700 flex items-center gap-1.5"
                  >
                    <Trash2 size={12} /> Request Erasure
                  </button>
                )}

                {erasureState === "confirm" && (
                  <div className="mt-3 space-y-2">
                    <p className="text-red-700 text-xs font-medium">⚠️ This will delete all records. Regulatory holds (PEP/Sanctioned) prevent deletion.</p>
                    <textarea
                      value={erasureReason}
                      onChange={(e) => setErasureReason(e.target.value)}
                      placeholder="Reason for erasure request (optional)"
                      className="w-full border border-red-200 rounded-lg px-3 py-2 text-xs resize-none h-16 focus:outline-none bg-white"
                    />
                    <div className="flex gap-2">
                      <button onClick={submitRight} className="px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-medium hover:bg-red-700">Confirm</button>
                      <button onClick={() => setErasureState("idle")} className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs text-slate-700 hover:bg-white">Cancel</button>
                    </div>
                  </div>
                )}

                {erasureState === "submitted" && (
                  <p className="mt-3 text-xs text-green-700 bg-green-50 px-3 py-2 rounded-lg">
                    ✅ Request submitted. You will receive confirmation within 30 days.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
