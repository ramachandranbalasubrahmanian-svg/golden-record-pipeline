# Golden Record Pipeline

**Live Demo:** https://golden-records-demo.lovable.app  
**API:** https://refreshing-liberation-production-8a25.up.railway.app/docs  

A production-deployed, end-to-end customer data platform for fintech compliance — entity resolution, survivorship, attribute lineage, vector RAG, and GDPR tooling — running on 89,198 real-scale synthetic records.

---

## What It Does

Banks collect customer data from multiple systems. The same customer appears in CBS, CRM, KYC, and RISK platforms with slightly different names, addresses, or dates. This pipeline:

1. **Ingests** all source records with DQ scoring and quarantine
2. **Resolves** duplicate identities across systems using fuzzy matching + ML clustering
3. **Applies survivorship** — picks the most trusted value for each attribute using source trust weights, recency, and regulatory lock
4. **Produces a Golden Record** — one authoritative, entity-resolved customer profile with full lineage
5. **Indexes everything** into pgvector for natural-language compliance queries
6. **Exposes a dual-persona API** — compliance officer view (full data) and customer self-service view (filtered)

---

## Live Stats

| Metric | Value |
|--------|-------|
| Source records ingested | 89,198 |
| Golden records produced | 20,502 |
| Multi-source customers | 51.9% |
| RAG chunks indexed | 35,000 |
| Transactions | 150,000 |
| Avg confidence score | 0.637 |
| PEP customers | 99 |
| Sanctioned customers | 20 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Source Systems (CSV)                      │
│   CBS (core banking) · CRM · KYC platform · RISK engine     │
└────────────────────────┬────────────────────────────────────┘
                         │
                    01_seed.py
              (load, parse, normalise)
                         │
                    02_dq.py
         (completeness · format · consistency)
                         │
                    03_er.py
      (fuzzy match · Soundex/Metaphone · ML clustering)
                         │
               04_survivorship.py
     (trust weights · recency · regulatory lock · lineage)
                         │
               05_rag_index.py
        (sentence-transformers · pgvector · 35k chunks)
                         │
           ┌─────────────┴──────────────┐
           │    FastAPI (Railway)        │
           │  /customers  /rag/query     │
           │  /stewardship  /gdpr        │
           └─────────────┬──────────────┘
                         │
               Lovable Frontend
         Dashboard · Chat · Portal · GDPR
```

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| API | FastAPI + uvicorn | Auto-docs at `/docs` |
| Database | PostgreSQL 16 + pgvector | Vector similarity search |
| ORM | SQLAlchemy 2.0 | Sync + async sessions |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | Free, 384-dim, runs locally |
| Vector search | pgvector cosine + BM25 + RRF | Hybrid retrieval |
| ER matching | Jaro-Winkler · Soundex · Metaphone · Levenshtein | 20 match features |
| Frontend | React + TanStack Query (Lovable) | |
| Deployment | Railway (backend + Postgres) | $5/mo Hobby plan |
| Data generation | Faker (seed 42) | 4 source systems, realistic conflicts |

---

## Key Features

### Entity Resolution
- 20-feature comparison: name similarity (Jaro-Winkler, Soundex, Metaphone), email, DOB, phone, address
- Reciprocal Rank Fusion for hybrid vector + BM25 re-ranking
- Union-Find clustering for transitive duplicate groups
- 19,835 match pairs identified, 92–95% confidence

### Dynamic Survivorship
- Per-attribute trust weights by source system (KYC > CRM > CBS for compliance fields)
- Regulatory lock: KYC, PEP, sanctions fields frozen once verified — cannot be overwritten
- Recency boost: more recent records score higher
- Full attribute lineage stored: winning source, losing sources, confidence

### Hybrid RAG
- Chunks each golden record into typed segments: identity, kyc_compliance, risk_profile, sanctions_pep, etc.
- Dual-persona query: `internal` (full compliance data) vs `customer` (filtered self-service)
- Hallucination validation via word-overlap grounding check
- Every query audit-logged with sources, confidence, latency

### Stewardship Queue
- Match pairs below auto-merge threshold routed to human review
- Side-by-side comparison with feature scores
- Approve / Reject with reviewer notes

### GDPR
- Right-to-erasure request submission and tracking
- Cascade delete across all tables respecting FK constraints
- Full audit log

---

## Running Locally

### Prerequisites
- Python 3.11+
- PostgreSQL 16 with pgvector extension
- Node.js 18+ (frontend only)

### Backend

```bash
git clone git@github.com:ramachandranbalasubrahmanian-svg/golden-record-pipeline.git
cd golden-record-pipeline/backend

# Install dependencies
pip install -r requirements.txt

# Set env vars
cp ../.env.example .env
# Edit .env: set DATABASE_URL, API_KEY

# Init DB
python scripts/01_init_db.py

# Run full pipeline (~40 min)
bash scripts/run_pipeline.sh

# Patch live data quality issues
python scripts/06_patch_data.py

# Start API
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/docs
```

### Pipeline Steps (manual)

```bash
python data/generate_all.py        # Generate synthetic CSVs
python scripts/01_seed.py          # Load source records
python scripts/02_dq.py            # Score data quality
python scripts/03_er.py            # Entity resolution
python scripts/04_survivorship.py  # Build golden records
python scripts/01_seed.py          # Seed transactions (2nd pass)
python scripts/05_rag_index.py     # Build RAG vector index
python scripts/06_patch_data.py    # Fix data quality issues
```

### Frontend (optional — Lovable)

The frontend is hosted on Lovable. To run locally:
```bash
cd frontend
npm install
npm run dev
```

Point `VITE_API_URL` to `http://localhost:8000`.

---

## API Quick Reference

Auth: `X-API-Key: demo-key-2026`

```bash
# Health
curl https://refreshing-liberation-production-8a25.up.railway.app/health

# Customer stats
curl -H "X-API-Key: demo-key-2026" \
  https://refreshing-liberation-production-8a25.up.railway.app/customers/stats/summary

# RAG compliance query
curl -X POST -H "X-API-Key: demo-key-2026" -H "Content-Type: application/json" \
  -d '{"question":"Who are PEP customers with verified KYC?","persona":"internal"}' \
  https://refreshing-liberation-production-8a25.up.railway.app/rag/query

# Expiring KYC (next 30 days)
curl -H "X-API-Key: demo-key-2026" \
  "https://refreshing-liberation-production-8a25.up.railway.app/customers/at-risk/expiring-kyc?days_ahead=30"

# Stewardship queue
curl -H "X-API-Key: demo-key-2026" \
  https://refreshing-liberation-production-8a25.up.railway.app/stewardship/queue
```

Full API reference: [API_DOCS.md](./API_DOCS.md)

---

## Project Structure

```
golden-record-portfolio/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers
│   │   │   ├── golden_records.py
│   │   │   ├── rag_query.py
│   │   │   ├── stewardship.py
│   │   │   ├── lineage_api.py
│   │   │   └── gdpr.py
│   │   ├── models/
│   │   │   ├── db_models.py   # SQLAlchemy models
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── pipeline/
│   │   │   ├── retrieval.py   # Hybrid BM25 + pgvector retrieval
│   │   │   ├── rag.py         # Answer generation + hallucination check
│   │   │   ├── query_pipeline.py
│   │   │   ├── survivorship.py
│   │   │   └── entity_resolution.py
│   │   ├── config.py
│   │   └── main.py
│   ├── data/
│   │   └── generate_all.py    # Synthetic data generator
│   ├── scripts/
│   │   ├── 01_init_db.py      # Create tables + extensions
│   │   ├── 01_seed.py         # Load CSVs → source_records
│   │   ├── 02_dq.py           # DQ scoring
│   │   ├── 03_er.py           # Entity resolution
│   │   ├── 04_survivorship.py # Golden records + lineage
│   │   ├── 05_rag_index.py    # Vector indexing
│   │   ├── 06_patch_data.py   # Data quality patches
│   │   └── run_pipeline.sh    # Run all steps
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/             # Dashboard, CustomerPortal, etc.
│       ├── features/grp/      # GRP feature components
│       └── lib/api.ts         # API client
├── README.md
├── API_DOCS.md
├── RUNBOOK.md
└── DEMO_SCRIPT.md
```

---

## Deployment

Deployed on Railway. See [RUNBOOK.md](./RUNBOOK.md) for step-by-step deployment guide.

---

## Disclaimer

This is a portfolio project using fully synthetic data generated with Faker. No real customer information is used. All names, addresses, and financial data are fictional.
