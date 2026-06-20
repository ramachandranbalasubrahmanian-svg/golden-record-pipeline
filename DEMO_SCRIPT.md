# Golden Record Pipeline — Demo Script

**URL:** https://golden-records-demo.lovable.app  
**API:** https://refreshing-liberation-production-8a25.up.railway.app  
**Duration:** ~15 minutes

---

## Opening Narrative

> "Banks and fintechs collect customer data from multiple systems — core banking, CRM, KYC platforms, risk engines. The same customer appears in all of them, with slight differences in spelling, address, or phone. The Golden Record Pipeline solves this: it ingests all those sources, resolves duplicate identities, applies survivorship rules to pick the most trusted value for each field, and produces a single authoritative view — the Golden Record. It also provides a compliance-grade audit trail, a conversational RAG interface for analysts, and GDPR tooling."

---

## Scene 1 — Executive Dashboard (2 min)

**Navigate to:** Dashboard tab

**Talking points:**
- "We're processing **20,502 unique customers** resolved from **89,198 source records** across 4 systems: CBS, CRM, KYC, and RISK."
- "**51.9% of customers** appear in more than one source system — those are the ones that needed identity resolution."
- "KYC posture at a glance: 12,280 VERIFIED, 1,571 PENDING, 1,162 EXPIRED."
- "99 PEP customers. 20 sanctioned. Average confidence score: 0.637."
- "**200 customers have KYC expiring within 30 days** — the system surfaces them automatically."

**What to show:** The stat cards, the KYC breakdown chart, the risk rating distribution.

---

## Scene 2 — Customer 360 View (3 min)

**Navigate to:** Customers tab → search for any customer

**Demo customer:** `d8ed19ca-705d-469c-8d19-75d9d9f776c6` (Angelika Davids)

**Talking points:**
- "Every golden record shows the consolidated profile — name, DOB, address, KYC status, risk rating — with a confidence score showing how much we trust this record."
- "Source count tells us how many systems contributed data. Multi-source records have higher confidence."
- "Click into a customer to see their full profile, transaction history, and data lineage."

**What to show:**
1. Customer list with search
2. Full profile for Angelika Davids
3. Transactions tab — real transaction history
4. Lineage tab — which source system won each field

---

## Scene 3 — Data Lineage & Source Wins (2 min)

**Navigate to:** Lineage Visualizer tab

**Talking points:**
- "When two sources disagree on a field — say CRM says the customer's city is 'London' and CBS says 'LONDON' — the survivorship engine decides which one wins."
- "This chart shows which source system wins the most attributes globally. CRM tends to win contact fields; KYC wins compliance fields; CBS wins financial fields."
- "Every attribute win is stored as lineage, so a compliance officer can always trace back to the original source."

**What to show:** The pie/bar chart of source wins by attribute.

---

## Scene 4 — RAG Compliance Chat (3 min)

**Navigate to:** Compliance Chat tab

**Demo queries to run:**
1. `"Who are the PEP customers with verified KYC status?"` → persona: Internal
2. `"Summarize compliance posture for high risk customers"` → persona: Internal
3. `"What is the KYC expiry date for this customer?"` (with entity ID set to Angelika Davids) → persona: Customer

**Talking points:**
- "Compliance analysts spend hours writing SQL queries or digging through systems. This RAG interface lets them ask questions in plain English."
- "Every answer is grounded in the golden record chunks — 35,000 indexed text chunks from all 20,502 customers."
- "The system shows which chunks it retrieved, with similarity scores, so analysts can verify sources."
- "We have two personas: Internal (full data, risk scores, PEP flags) and Customer (filtered view, no risk data exposed)."
- "Every query is audit-logged — who asked what, when, what answer was returned."

**What to show:**
1. Type a question, show the answer appearing
2. Expand the "8 sources →" to show retrieved chunks
3. Show the "Fact-checked" badge

---

## Scene 5 — Stewardship Queue (2 min)

**Navigate to:** Stewardship tab

**Talking points:**
- "Entity resolution is 92–95% confident on our 50 pending pairs. The human stewardship queue captures the cases where the system isn't sure enough to auto-merge."
- "A reviewer sees both records side-by-side, the match features (name similarity, email match, address overlap), and can Approve or Reject the merge."
- "This is the human-in-the-loop layer that keeps the golden records accurate."

**What to show:**
1. Queue list with match probabilities
2. Click on a pair → show match evidence (feature scores)
3. Approve one → show it disappears from queue

---

## Scene 6 — Customer Portal / Self-Service (2 min)

**Navigate to:** Customer Portal tab

**Talking points:**
- "The same golden record powers the customer-facing view. A customer logs in and sees their own consolidated profile."
- "They can chat with an AI assistant that answers questions about their account — but the persona filters out internal data like risk scores or PEP flags."
- "They can submit GDPR erasure requests directly. The request is logged, status is tracked, and the bank can fulfill it with full audit trail."

**What to show:**
1. Profile tab — customer details
2. Chat tab — ask "What is my account status?"
3. Privacy tab — submit erasure request form

---

## Scene 7 — GDPR & Compliance (1 min)

**Talking points:**
- "Every erasure request is stored with requester identity, reason, and status. The pipeline can be triggered to suppress the customer's data across all source systems."
- "The audit log for RAG queries means every AI-generated compliance answer is traceable."
- "KYC expiry alerts mean the bank never misses a re-verification deadline."

---

## Closing

> "What you've just seen is a production-grade data platform: 89,000 source records, 20,500 resolved golden records, a vector RAG index over 35,000 chunks, entity resolution with human-in-the-loop review, and a compliance-grade audit trail — all running on a free-tier Railway deployment. The architecture is cloud-native, the pipeline is idempotent, and every component is replaceable."

**Questions to anticipate:**
- *"How long does the pipeline take?"* → ~40 min for 89k records end-to-end on a single Postgres instance.
- *"Can it scale?"* → Yes — the pipeline is stateless; add workers for parallelism.
- *"What LLM does it use?"* → Free sentence-transformers for embeddings (all-MiniLM-L6-v2, 384-dim), template-based answer generation. No OpenAI quota needed.
- *"How do you handle conflicts?"* → Survivorship rules: most recent KYC wins compliance fields, highest-confidence source wins identity fields, all losers stored as lineage.
