const BASE = import.meta.env.VITE_API_URL ?? "https://refreshing-liberation-production-8a25.up.railway.app";
const KEY = import.meta.env.VITE_API_KEY ?? "demo-key-2026";

const headers = () => ({
  "Content-Type": "application/json",
  "X-API-Key": KEY,
});

async function get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const url = new URL(BASE + path);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Golden Records ────────────────────────────────────────────────────────────
export const listCustomers = (p?: Record<string, string | number | boolean>) =>
  get("/customers", p);
export const getCustomer = (id: string) => get(`/customers/${id}`);
export const getCustomerFull = (id: string) => get(`/customers/${id}/full`);
export const getLineage = (id: string) => get(`/customers/${id}/lineage`);
export const getTransactions = (id: string, p?: Record<string, string | number>) =>
  get(`/customers/${id}/transactions`, p);
export const getStats = () => get("/customers/stats/summary");
export const getExpiringKYC = (days = 30) =>
  get("/customers/at-risk/expiring-kyc", { days_ahead: days });

// ── RAG ───────────────────────────────────────────────────────────────────────
export const ragQuery = (body: { question: string; entity_id?: string; persona?: string; top_k?: number }) =>
  post("/rag/query", body);
export const ragHistory = (entity_id?: string) =>
  get("/rag/history", entity_id ? { entity_id } : undefined);
export const ragStats = () => get("/rag/stats");

// ── Stewardship ───────────────────────────────────────────────────────────────
export const getQueue = (p?: Record<string, string | number>) =>
  get("/stewardship/queue", p);
export const stewardshipDecide = (pair_id: string, decision: "approved" | "rejected", notes?: string) =>
  post("/stewardship/decide", { pair_id, decision, reviewer_notes: notes });
export const stewardshipStats = () => get("/stewardship/stats");
export const pairEvidence = (pair_id: string) =>
  get(`/stewardship/pair/${pair_id}/evidence`);
export const autoApprove = (threshold = 0.95) =>
  post("/stewardship/auto-approve", { threshold, max_records: 1000 });

// ── Lineage ───────────────────────────────────────────────────────────────────
export const sourceWins = () => get("/lineage/source-wins/summary");
export const activeConflicts = (customer_id?: string) =>
  get("/lineage/conflicts/active", customer_id ? { customer_id } : undefined);

// ── GDPR ──────────────────────────────────────────────────────────────────────
export const erasureLog = (status?: string) =>
  get("/gdpr/erasure-log", status ? { status } : undefined);
export const submitErasure = (customer_id: string, requester_email: string, reason: string) =>
  post("/gdpr/erasure-request", { customer_id, requester_email, reason });

// ── Health ────────────────────────────────────────────────────────────────────
export const health = () => get("/health");

// ── Mock data for offline dev ─────────────────────────────────────────────────
export const MOCK_STATS = {
  total_customers: 5000,
  by_risk_rating: { LOW: 3550, MEDIUM: 1200, HIGH: 200, CRITICAL: 50 },
  by_kyc_status: { VERIFIED: 4375, PENDING: 375, FAILED: 100, EXPIRED: 150 },
  pep_count: 50,
  sanctioned_count: 10,
  avg_confidence_score: 0.847,
  avg_source_count: 2.3,
  high_confidence_pct: 0.72,
  multi_source_pct: 0.68,
};
