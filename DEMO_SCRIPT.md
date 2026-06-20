# Golden Record Pipeline — Video Demo Script

**Total runtime:** ~12–15 minutes  
**Live URL:** https://golden-records-demo.lovable.app  
**Format:** Screen recording with voiceover narration  

---

## PRE-RECORDING SETUP

Before hitting record:
- [ ] Open https://golden-records-demo.lovable.app in a clean browser (no extensions visible)
- [ ] Set browser zoom to 90% for more screen space
- [ ] Close all other tabs
- [ ] Open Railway console in a separate window (minimised — for backup)
- [ ] Clear browser history/autofill so no personal data shows
- [ ] Resolution: 1920×1080
- [ ] Microphone: test levels

---

## INTRO TITLE CARD
**[00:00 – 00:20]**

> **[SCREEN: Black screen with white text overlay]**  
> *"Golden Record Pipeline"*  
> *"Enterprise Customer Data Platform"*  
> *"Entity Resolution · Survivorship · Compliance RAG"*

**[NARRATOR]**
> "In banking and fintech, the same customer exists in multiple systems — core banking, CRM, KYC, and risk engines — with slightly different data in each. This creates duplicates, compliance gaps, and no single source of truth. The Golden Record Pipeline solves that."

---

## SCENE 1 — ARCHITECTURE OVERVIEW
**[00:20 – 01:30]**

> **[SCREEN: Show the architecture diagram from README or a slide]**

**[NARRATOR]**
> "The system ingests customer records from four source systems — CBS, CRM, KYC, and a Risk engine — representing 89,000 records. It applies data quality scoring, resolves duplicate identities using fuzzy matching and ML clustering, and produces 20,502 unique Golden Records. Each one has a confidence score, attribute-level lineage, and is indexed into a vector database for AI-powered compliance queries."

**[PAUSE 1 second]**

> "Let me show you the live system."

---

## SCENE 2 — EXECUTIVE DASHBOARD
**[01:30 – 03:30]**

> **[ACTION: Navigate to https://golden-records-demo.lovable.app → Dashboard tab]**

> **[SCREEN: Dashboard with stat cards and charts visible]**

**[NARRATOR]**
> "This is the executive dashboard. We're looking at 20,502 unique customers resolved from 89,198 source records across four systems."

**[ACTION: Point cursor to stat cards one by one]**

**[NARRATOR]**
> "51.9% of customers appeared in more than one source system — those are the ones that needed identity resolution. Without this pipeline, they'd be counted as separate people."

**[ACTION: Move cursor to KYC status breakdown]**

**[NARRATOR]**
> "KYC posture at a glance — 12,280 verified, 1,571 pending, 1,162 expired. And here — 200 customers with KYC expiring in the next 30 days. The system surfaces this automatically, so the compliance team never misses a re-verification deadline."

**[ACTION: Point to PEP count and sanctioned count]**

**[NARRATOR]**
> "99 PEP customers and 20 sanctioned customers identified across the portfolio. Average confidence score of 0.637 — meaning the system knows exactly how much to trust each golden record."

---

## SCENE 3 — CUSTOMER 360 VIEW
**[03:30 – 05:30]**

> **[ACTION: Click Customers tab → search or scroll to find a customer]**

> **[SCREEN: Customer list showing names, KYC status badges, risk ratings]**

**[NARRATOR]**
> "Every golden record is a single, authoritative customer view — consolidated from however many source systems had data on that person."

> **[ACTION: Click on any customer with VERIFIED status to open their profile]**

> **[SCREEN: Full customer profile card]**

**[NARRATOR]**
> "The confidence score tells us how reliable this record is. A customer seen in two or more systems scores higher than one seen only in core banking. The source count shows exactly how many systems contributed."

**[ACTION: Click Transactions tab]**

**[NARRATOR]**
> "Real transaction history is linked to the golden record — not to the fragmented source IDs. So when a compliance analyst pulls a customer, they see the complete picture."

**[ACTION: Click Lineage tab]**

**[NARRATOR]**
> "And here's the lineage. For every attribute — name, email, address, KYC status — you can see which source system won and which ones were overridden. This is the audit trail that regulators want to see."

---

## SCENE 4 — DATA LINEAGE VISUALISER
**[05:30 – 06:45]**

> **[ACTION: Click Lineage Visualizer tab in main nav]**

> **[SCREEN: Pie or bar chart showing source wins by attribute]**

**[NARRATOR]**
> "The lineage visualiser shows which source system wins the most attributes globally. CRM tends to win contact fields — email, phone. KYC wins compliance fields. CBS wins core banking fields. RISK wins risk ratings."

**[PAUSE 1 second]**

**[NARRATOR]**
> "Every one of these wins is stored at the attribute level — so a compliance officer can always trace back to the original record that won."

---

## SCENE 5 — RAG COMPLIANCE CHAT
**[06:45 – 09:30]**

> **[ACTION: Click Compliance Chat tab]**

> **[SCREEN: Chat interface with persona selector and query input]**

**[NARRATOR]**
> "This is the compliance chat interface. Analysts spend hours writing SQL or digging through systems. Here they can ask questions in plain English — grounded in the 35,000 indexed chunks from all 20,502 golden records."

**[ACTION: Make sure persona is set to "Internal" → type the first query]**

**[TYPE: "Who are the PEP customers with verified KYC status?"]**

> **[SCREEN: Answer appearing with customer names and sources]**

**[NARRATOR]**
> "The system retrieves the most relevant chunks using hybrid search — pgvector cosine similarity combined with BM25 keyword ranking, then re-ranked with Reciprocal Rank Fusion. The answer is grounded exclusively in the retrieved data."

**[ACTION: Click "8 sources →" to expand the source chunks]**

**[NARRATOR]**
> "Here are the source chunks — each one showing its similarity score and which part of the golden record it came from. The Fact-checked badge means the answer overlaps significantly with the source content."

**[ACTION: Clear chat → type second query]**

**[TYPE: "Summarise compliance posture for high risk customers"]**

> **[SCREEN: Answer showing risk breakdown]**

**[NARRATOR]**
> "245 HIGH risk customers, 49 CRITICAL. The system pulls this from the risk_profile chunks across the customer base."

**[ACTION: Change persona dropdown to "Customer"]**

**[TYPE: "What is my account status?"]**

**[NARRATOR]**
> "Now switch to the customer persona. The same underlying data — but internal fields like risk scores, PEP status, and sanctions flags are filtered out. The customer sees only what they're allowed to see. Same engine, different lens."

**[PAUSE 1 second]**

**[NARRATOR]**
> "And every single query is audit-logged — who asked, what was asked, what answer was returned, which chunks were used, and the latency. Fully traceable for regulatory review."

---

## SCENE 6 — STEWARDSHIP QUEUE
**[09:30 – 11:00]**

> **[ACTION: Click Stewardship tab]**

> **[SCREEN: Queue with 50 pending pairs, match probabilities, source systems]**

**[NARRATOR]**
> "Entity resolution auto-merges pairs it's confident about — 92 to 95 percent confidence in this dataset. The cases it's less sure about go into the stewardship queue for human review."

**[ACTION: Point to the match probability badges]**

**[NARRATOR]**
> "50 pairs pending review. Each one shows both records, the source systems they came from, and the match features — name similarity, email match, DOB match — with individual scores."

**[ACTION: Click on one pair to expand match evidence]**

**[NARRATOR]**
> "Here — first name and last name are exact matches, email matches, address matches. But DOB doesn't match. The system is 92% sure this is the same person. A human reviewer makes the final call."

**[ACTION: Click Approve on one pair]**

**[NARRATOR]**
> "Approved — the records are merged into a single golden record with lineage updated. This is the human-in-the-loop layer that keeps the data accurate."

---

## SCENE 7 — CUSTOMER PORTAL
**[11:00 – 12:30]**

> **[ACTION: Click Customer Portal tab]**

> **[SCREEN: Customer portal showing Angelika Davids profile]**

**[NARRATOR]**
> "The same golden record also powers the customer-facing portal. A customer logs in and sees their consolidated profile — name, contact details, KYC status, expiry date."

**[ACTION: Click Chat tab within the portal]**

**[TYPE: "What is my KYC status?"]**

> **[SCREEN: Friendly response with no internal data]**

**[NARRATOR]**
> "The AI assistant answers in plain language — no internal jargon, no risk scores. The persona filter ensures internal compliance data never leaks to the customer view."

**[ACTION: Click Privacy Rights tab]**

**[NARRATOR]**
> "And customers can submit a GDPR right-to-erasure request directly. The request is logged, assigned a status, and tracked through fulfillment — with a complete audit trail."

**[ACTION: Fill in the erasure form and submit]**

**[SCREEN: Confirmation with request ID and PENDING status]**

**[NARRATOR]**
> "Request submitted. Compliance team gets notified. Customer gets a reference ID."

---

## SCENE 8 — CLOSING
**[12:30 – 13:30]**

> **[SCREEN: Return to Dashboard — all stats visible]**

**[NARRATOR]**
> "What you've just seen is a production-deployed data platform — 89,000 source records, 20,500 resolved golden records, a vector RAG index over 35,000 chunks, entity resolution with human review, attribute lineage, and GDPR tooling — all running on Railway and Lovable."

**[PAUSE 1 second]**

**[NARRATOR]**
> "The pipeline is fully open source. The architecture is cloud-native and the components are modular — swap in a different LLM, a different vector store, or a different frontend without touching the pipeline logic. The embedding and answer generation use free, locally-run models — no OpenAI quota needed."

**[PAUSE 1 second]**

**[NARRATOR]**
> "Links to the live demo, GitHub repo, and full API documentation are in the description."

---

## OUTRO TITLE CARD
**[13:30 – 14:00]**

> **[SCREEN: Black background, white text]**  
> *"Golden Record Pipeline"*  
> *"github.com/ramachandranbalasubrahmanian-svg/golden-record-pipeline"*  
> *"Live: golden-records-demo.lovable.app"*  
> *"API: refreshing-liberation-production-8a25.up.railway.app/docs"*

---

## VIDEO EDITING NOTES

| Timestamp | Edit note |
|-----------|-----------|
| 00:00 | Add logo animation / intro music fade-in |
| 00:20 | Cut to screen recording |
| 01:30 | Zoom into stat cards for emphasis |
| 03:30 | Add lower-third label "Customer 360 View" |
| 05:30 | Add lower-third label "Data Lineage" |
| 06:45 | Add lower-third label "RAG Compliance Chat" |
| 06:45 | Add screen highlight on persona selector |
| 09:30 | Add lower-third label "Human Stewardship" |
| 11:00 | Add lower-third label "Customer Portal" |
| 12:30 | Fade dashboard back in |
| 13:30 | Fade to black + outro card |
| Throughout | Cursor highlight / zoom effect on key elements |

## B-ROLL SUGGESTIONS

- Architecture diagram animated (Mermaid or Figma export)
- Pipeline flowchart showing CSV → Golden Record progression
- pgvector chunk retrieval visualised as similarity scores
- Split-screen showing same customer in 4 different source systems vs. unified golden record
