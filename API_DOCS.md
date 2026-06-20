# Golden Record Pipeline — API Reference

**Base URL:** `https://refreshing-liberation-production-8a25.up.railway.app`  
**Auth:** All endpoints require `X-API-Key: demo-key-2026` header

---

## Health

### GET /health
Returns service health status.

**Response:**
```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Customers

### GET /customers
List golden records with pagination and filtering.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max records (1–500) |
| `offset` | int | 0 | Pagination offset |
| `kyc_status` | string | — | Filter: VERIFIED, PENDING, FAILED, EXPIRED |
| `risk_rating` | string | — | Filter: LOW, MEDIUM, HIGH, CRITICAL |
| `is_pep` | bool | — | Filter PEP customers |
| `is_sanctioned` | bool | — | Filter sanctioned customers |
| `search` | string | — | Full-text search on name/email |

**Response:**
```json
{
  "items": [
    {
      "customer_id": "d8ed19ca-705d-469c-8d19-75d9d9f776c6",
      "full_legal_name": "Angelika Davids",
      "email": null,
      "kyc_status": "VERIFIED",
      "risk_rating": "LOW",
      "confidence_score": 0.72,
      "source_count": 2,
      "is_pep": false,
      "is_sanctioned": false
    }
  ],
  "total": 20502,
  "limit": 50,
  "offset": 0
}
```

---

### GET /customers/stats/summary
Aggregate statistics across all golden records.

**Response:**
```json
{
  "total_customers": 20502,
  "by_risk_rating": { "LOW": 4287, "MEDIUM": 1384, "HIGH": 245, "CRITICAL": 49 },
  "by_kyc_status": { "VERIFIED": 12280, "PENDING": 1571, "FAILED": 293, "EXPIRED": 1162 },
  "pep_count": 99,
  "sanctioned_count": 20,
  "avg_confidence_score": 0.637,
  "avg_source_count": 1.72,
  "high_confidence_pct": 0.1497,
  "multi_source_pct": 0.5199
}
```

---

### GET /customers/at-risk/expiring-kyc
Customers whose KYC expires soon.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days_ahead` | int | 30 | Look-ahead window in days |

**Response:** Array of customer objects with `kyc_expiry_at` field.

---

### GET /customers/{customer_id}
Get single golden record.

**Path param:** `customer_id` — UUID

**Response:**
```json
{
  "customer_id": "d8ed19ca-705d-469c-8d19-75d9d9f776c6",
  "first_name": "Angelika",
  "last_name": "Davids",
  "full_legal_name": "Angelika Davids",
  "date_of_birth": "1979-04-12",
  "email": null,
  "phone": "+27 21 555 0142",
  "address_line1": "14 Long Street",
  "city": "Cape Town",
  "country": "ZAF",
  "nationality": "ZAF",
  "kyc_status": "VERIFIED",
  "kyc_tier": "TIER_2",
  "kyc_verified_at": "2025-06-20T12:22:56",
  "kyc_expiry_at": "2027-06-20T12:22:56",
  "risk_rating": "LOW",
  "risk_score": null,
  "is_pep": false,
  "pep_type": null,
  "is_sanctioned": false,
  "sanctions_list": null,
  "confidence_score": 0.72,
  "source_count": 2,
  "winning_sources": null,
  "cluster_id": "cluster-abc123",
  "created_at": "2026-06-20T10:00:00",
  "updated_at": "2026-06-20T10:00:00"
}
```

---

### GET /customers/{customer_id}/full
Full profile including source records and lineage.

**Response:** Same as above plus:
```json
{
  "source_records": [ ... ],
  "lineage": [ ... ],
  "transactions_count": 7
}
```

---

### GET /customers/{customer_id}/lineage
Attribute-level lineage showing which source won each field.

**Response:**
```json
[
  {
    "attribute": "email",
    "winning_source": "CRM",
    "winning_value": "angelika@example.com",
    "competing_sources": ["CBS", "CRM"],
    "confidence": 0.85
  }
]
```

---

### GET /customers/{customer_id}/transactions
Transaction history for a customer.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 100 | Max records |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "items": [
    {
      "transaction_id": "txn-uuid",
      "customer_id": "d8ed19ca-...",
      "transaction_date": "2024-03-15",
      "amount": 1250.00,
      "currency": "ZAR",
      "transaction_type": "CREDIT",
      "channel": "ONLINE",
      "counterparty_name": "ACME Corp",
      "counterparty_country": "ZAF",
      "is_suspicious": false,
      "suspicious_reason": null
    }
  ],
  "total": 7
}
```

---

## RAG Compliance Chat

### POST /rag/query
Ask a compliance question grounded in golden record data.

**Request:**
```json
{
  "question": "Who are the PEP customers with verified KYC?",
  "entity_id": null,
  "persona": "internal",
  "top_k": 8
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Natural language question |
| `entity_id` | UUID | No | Scope to one customer |
| `persona` | string | No | `internal` (compliance, full data) or `customer` (self-service, filtered) |
| `top_k` | int | No | Number of chunks to retrieve (default 8) |

**Response:**
```json
{
  "answer": "Based on retrieved compliance records:\n\n• Customer Théo Sales (ID: 54814a89...)\n...",
  "sources": [
    {
      "chunk_id": "63302520-...",
      "chunk_type": "sanctions_pep",
      "content_preview": "Customer Théo Sales (ID: 54814a89...)\n[CHUNK_TYPE: SANCTIONS_PEP]\nPEP Status: No\n...",
      "similarity_score": 0.666,
      "entity_id": "54814a89-bd37-45b0-a2cd-9763b132c8fb"
    }
  ],
  "entity_id": null,
  "hallucination_check_passed": true,
  "confidence": 0.666,
  "tokens_used": 0,
  "latency_ms": 412
}
```

---

### GET /rag/history
Query audit log.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `entity_id` | UUID | Filter by customer |
| `limit` | int | Max results (default 50) |

---

### GET /rag/stats
RAG usage statistics.

**Response:**
```json
{
  "total_queries": 42,
  "avg_latency_ms": 380,
  "hallucination_pass_rate": 0.95,
  "total_chunks": 35000
}
```

---

## Stewardship Queue

### GET /stewardship/queue
List pending human-review pairs.

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max results |
| `offset` | int | 0 | Pagination |
| `status` | string | `open` | Filter by status |

**Response:**
```json
{
  "items": [
    {
      "pair_id": "0f9c7b79-...",
      "record_a_id": "879db8b2-...",
      "record_b_id": "adc08ec9-...",
      "source_a": "CRM",
      "source_b": "CRM",
      "match_probability": 0.92,
      "match_features": {
        "email_exact_match": 1.0,
        "first_name_jaro_winkler": 1.0,
        "last_name_jaro_winkler": 1.0,
        "dob_exact_match": 0.0
      },
      "status": "pending"
    }
  ],
  "total": 50
}
```

---

### POST /stewardship/decide
Approve or reject a match pair.

**Request:**
```json
{
  "pair_id": "0f9c7b79-6a93-4683-b63b-7322b9f47d60",
  "decision": "approved",
  "reviewer_notes": "Same person, different branch records"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `decision` | `approved` / `rejected` | Merge decision |
| `reviewer_notes` | string | Optional free text |

---

### GET /stewardship/pair/{pair_id}/evidence
Full evidence for a match pair including both raw records.

---

### GET /stewardship/stats
Queue statistics.

```json
{
  "total_open": 50,
  "total_approved": 0,
  "total_rejected": 0,
  "avg_match_probability": 0.92
}
```

---

### POST /stewardship/auto-approve
Auto-approve pairs above a confidence threshold.

**Request:**
```json
{ "threshold": 0.95, "max_records": 1000 }
```

---

## Lineage

### GET /lineage/source-wins/summary
Which source system wins each attribute globally.

**Response:**
```json
{
  "email": { "CRM": 4965, "KYC": 210 },
  "kyc_status": { "KYC": 5180, "CBS": 320 },
  "risk_rating": { "RISK": 2100, "KYC": 800 }
}
```

---

### GET /lineage/conflicts/active
Active attribute conflicts (same field, different values across sources).

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `customer_id` | UUID | Filter to one customer |

---

## GDPR

### POST /gdpr/erasure-request
Submit a right-to-erasure request.

**Request:**
```json
{
  "customer_id": "d8ed19ca-705d-469c-8d19-75d9d9f776c6",
  "requester_email": "customer@example.com",
  "reason": "No longer a customer"
}
```

**Response:**
```json
{
  "request_id": "era-uuid",
  "status": "PENDING",
  "created_at": "2026-06-20T12:00:00"
}
```

---

### GET /gdpr/erasure-log
List all erasure requests.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter: PENDING, FULFILLED, REJECTED |

---

## Error Responses

All errors return:
```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid `X-API-Key` |
| 404 | Customer or resource not found |
| 422 | Validation error (bad request body) |
| 500 | Internal server error |
