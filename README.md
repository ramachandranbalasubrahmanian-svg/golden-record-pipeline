# Golden Record RAG Pipeline

A portfolio project demonstrating enterprise-grade customer data management for fintech compliance: entity resolution across 4 source systems, survivorship with regulatory lock, attribute-level lineage, and a natural-language RAG query interface backed by pgvector hybrid retrieval.

## What It Demonstrates

- **Entity Resolution** — LightGBM classifier + SHAP on 20 features, blocking via Soundex/Metaphone, Union-Find clustering
- **Dynamic Survivorship** — weighted scoring (trust × recency × completeness) with regulatory lock for KYC/PEP/sanctions attributes
- **Attribute-Level Lineage** — every golden record value traced back to its winning source system with competing alternatives
- **Hybrid RAG Retrieval** — pgvector cosine similarity + BM25 keyword search + Reciprocal Rank Fusion re-ranking
- **Dual-Persona API** — compliance officer vs customer views, with hallucination validation on every answer
- **GDPR Right to Erasure** — cascade delete across all 10 tables respecting FK constraints

## Quick Start

```bash
# 1. Copy env and add your OpenAI key
cp .env.example .env

# 2. Full setup (~35 min: DB + synthetic data + pipeline + ML model)
cd backend
make setup

# 3. Start the API
make dev
# → http://localhost:8000/docs
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI + asyncpg | Async Python, auto-docs |
| Database | PostgreSQL 16 + pgvector | Vector search natively |
| ORM | SQLAlchemy 2.0 async | Type-safe async queries |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim, cost-effective |
| LLM | GPT-4o-mini | Fast, cheap, accurate |
| ML | LightGBM + SHAP | Explainable ER classification |
| String matching | fuzzywuzzy + jellyfish | Jaro-Winkler, Soundex, Metaphone |
| Containers | Docker (DB only) | Minimal local footprint |

## API Docs

After `make dev`: http://localhost:8000/docs

Test the RAG endpoint:
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key-2026" \
  -d '{"question": "Show PEP customers with expired KYC", "persona": "internal"}'
```

## Scale (Synthetic Demo Data)

| Dataset | Count |
|---------|-------|
| Customers (master) | 5,000 |
| Source records (4 systems) | ~13,000 |
| Known duplicate pairs | 500 |
| Known attribute conflicts | 1,000 |
| Transactions | 150,000 |
| RAG chunks | ~35,000 |

## Pipeline Stages

```
CSV sources → 01_seed.py → 02_dq.py → 03_er.py → 04_survivorship.py → 05_rag_index.py
               (load)       (DQ score)  (cluster)   (golden records)    (embeddings)
```

## Portfolio Context

This is a portfolio demo with synthetic data. No real customer information is used.
All data generated via Faker with `random.seed(42)` for reproducibility.

Railway deploy: `make dump` exports a pg_dump for one-click restore to Railway PostgreSQL.
