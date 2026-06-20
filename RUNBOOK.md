# Golden Record Pipeline — Runbook

Complete guide to deploy and run the pipeline from scratch.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Pipeline scripts |
| Git | Any | Version control |
| Railway CLI | Latest | Deployment |
| Node.js | 18+ | Frontend (optional) |
| psql | Any | DB inspection |

Accounts needed:
- GitHub (free)
- Railway (Hobby plan, $5/mo — needed for Postgres >512MB)
- Lovable (free tier) — for frontend

---

## Step 1 — Clone the Repository

```bash
git clone git@github.com:ramachandranbalasubrahmanian-svg/golden-record-pipeline.git
cd golden-record-pipeline
```

---

## Step 2 — Set Up Railway Project

### 2a. Create Railway project
1. Go to https://railway.app → New Project
2. Choose **Empty Project**
3. Name it `golden-record-pipeline`

### 2b. Add PostgreSQL
1. In the project → **Add Service** → **Database** → **PostgreSQL**
2. Wait for it to go green
3. Click Postgres service → **Variables** tab
4. Copy `DATABASE_URL`

### 2c. Enable pgvector
In the Postgres service → **Query** tab, run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 2d. Deploy the backend
1. In the project → **Add Service** → **GitHub Repo**
2. Select `golden-record-pipeline` → root directory: `backend`
3. Railway auto-detects the Dockerfile

### 2e. Set environment variables
In the backend service → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | (paste from Postgres service) |
| `API_KEY` | `demo-key-2026` |
| `ENVIRONMENT` | `production` |
| `PORT` | `8000` |

### 2f. Set custom start command
In backend service → **Settings** → **Start Command**:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 2g. Get the public URL
Settings → **Networking** → **Generate Domain**  
Note the URL: `https://your-service.up.railway.app`

---

## Step 3 — Initialise the Database

In the Railway backend service → **Console** tab:

```bash
python scripts/01_init_db.py
```

Expected output:
```
Creating tables...
✓ Tables created
pgvector extension: OK
```

---

## Step 4 — Run the Pipeline

Each step must complete before the next. Run in the Railway Console:

### Step 4a — Generate synthetic data
```bash
python data/generate_all.py
```
Generates ~90k source records across CBS, CRM, KYC, RISK systems.  
**Duration:** ~2 min  
**Output files:** `data/raw/*.csv`

### Step 4b — Seed source records
```bash
python scripts/01_seed.py
```
Loads CSVs into `source_records` table with date parsing, KYC normalisation.  
**Duration:** ~5 min  
**Expected:** 89,198 source records

### Step 4c — Data Quality scoring
```bash
python scripts/02_dq.py
```
Scores each source record: completeness, format validity, consistency.  
**Duration:** ~3 min  
**Expected:** All 89,198 records scored, ~2% quarantined

### Step 4d — Entity Resolution
```bash
python scripts/03_er.py
```
Finds duplicate records across sources using name similarity, email, DOB, address.  
Forms clusters of matching records.  
**Duration:** ~10 min  
**Expected:** ~19,835 match pairs, clusters covering 20,502 unique entities

### Step 4e — Survivorship
```bash
python scripts/04_survivorship.py
```
For each cluster, picks the winning value for each attribute.  
Writes golden records and lineage entries.  
**Duration:** ~15 min  
**Expected:** 20,502 golden records

### Step 4f — Seed transactions
```bash
python scripts/01_seed.py
```
Run seed script a second time — this pass seeds 150,000 transactions.  
**Duration:** ~5 min

### Step 4g — RAG indexing
```bash
python scripts/05_rag_index.py
```
Chunks each golden record into text segments, embeds with `all-MiniLM-L6-v2` (free, local).  
**Duration:** ~10 min  
**Expected:** 35,000 RAG chunks in pgvector

### Or run all steps at once:
```bash
bash scripts/run_pipeline.sh
```
Logs to `/app/pipeline.log`. **Do not push to GitHub while this is running** — Railway redeploys kill the running container.

---

## Step 5 — Patch Live Data

Run once after the pipeline to fix data quality issues:

```bash
python scripts/06_patch_data.py
```

Then patch expiring KYC for demo:

```python
python3 -c "
import sys; sys.path.insert(0, '.')
from sqlalchemy import create_engine, text
from app.config import settings

with create_engine(settings.sync_database_url).begin() as db:
    db.execute(text('''
        UPDATE golden_records
        SET kyc_expiry_at = NOW() + (RANDOM() * INTERVAL '25 days')
        WHERE kyc_status = 'VERIFIED'
          AND kyc_expiry_at IS NOT NULL
          AND customer_id IN (
            SELECT customer_id FROM golden_records
            WHERE kyc_status = 'VERIFIED' ORDER BY RANDOM() LIMIT 200
          )
    '''))
"
```

---

## Step 6 — Connect the Frontend (Lovable)

1. Go to https://lovable.dev → Open your project
2. In Lovable chat: *"Update `src/lib/api.ts` to set BASE to `https://your-railway-url.up.railway.app`"*
3. Publish → **Deploy**
4. Visit `https://your-project.lovable.app`

---

## Step 7 — Verify Everything Works

```bash
# Health check
curl https://your-service.up.railway.app/health

# Stats
curl -H "X-API-Key: demo-key-2026" https://your-service.up.railway.app/customers/stats/summary

# RAG query
curl -X POST -H "X-API-Key: demo-key-2026" -H "Content-Type: application/json" \
  -d '{"question":"Who are PEP customers?","persona":"internal"}' \
  https://your-service.up.railway.app/rag/query

# Stewardship queue
curl -H "X-API-Key: demo-key-2026" https://your-service.up.railway.app/stewardship/queue
```

---

## Troubleshooting

### Container restarts mid-pipeline
Railway redeploys on every push. **Never push to GitHub while pipeline is running.**  
After a restart: re-run `python data/generate_all.py` (CSVs are ephemeral), then continue from the failed step.

### `::jsonb` or `::uuid` syntax error
SQLAlchemy conflicts with PostgreSQL cast syntax. Use `cast(:param as jsonb)` not `::jsonb`.

### Dates out of range
CBS uses DD/MM/YYYY format. `01_seed.py` handles this via `_parse_date()` and `SET datestyle = 'ISO, DMY'`.

### FK violation in transactions
`transactions.customer_id` must match a `golden_records.customer_id`. The seed script bridges via email lookup.

### pgvector dimension mismatch
If you change embedding models, drop and recreate `rag_chunks`:  
`05_rag_index.py` does this automatically.

### Stewardship queue empty
Run the stewardship seeding command from `06_patch_data.py` — it demotes 50 auto-merged pairs to pending.

---

## Architecture Overview

```
CSV Sources (CBS, CRM, KYC, RISK)
        ↓ 01_seed.py
   source_records (89,198)
        ↓ 02_dq.py
   DQ scores & quarantine
        ↓ 03_er.py
   entity_clusters + match_pairs (19,835)
        ↓ 04_survivorship.py
   golden_records (20,502) + lineage
        ↓ 05_rag_index.py
   rag_chunks (35,000, 384-dim vectors)
        ↓
   FastAPI (Railway) ← Lovable Frontend
```

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/scripts/01_seed.py` | Load CSVs → source_records |
| `backend/scripts/02_dq.py` | Score DQ for each record |
| `backend/scripts/03_er.py` | Entity resolution, clusters |
| `backend/scripts/04_survivorship.py` | Golden record resolution |
| `backend/scripts/05_rag_index.py` | Vector index with sentence-transformers |
| `backend/scripts/06_patch_data.py` | One-time data quality patches |
| `backend/scripts/run_pipeline.sh` | Run all steps in sequence |
| `backend/app/main.py` | FastAPI entrypoint |
| `backend/app/pipeline/retrieval.py` | RAG retrieval (hybrid BM25 + pgvector) |
| `backend/app/pipeline/rag.py` | Answer generation |
| `frontend/src/lib/api.ts` | Frontend API client |

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `API_KEY` | Yes | Auth header value (`X-API-Key`) |
| `ENVIRONMENT` | No | `production` or `development` |
| `PORT` | Yes | HTTP port (Railway sets this) |
| `OPENAI_API_KEY` | No | Not used — embeddings are free via sentence-transformers |
