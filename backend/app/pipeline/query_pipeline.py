"""Query pipeline — orchestrates retrieval → generation → validation."""
from __future__ import annotations
import time
import uuid
from typing import Optional

import openai
from sqlalchemy.orm import Session

from app.pipeline.retrieval import retrieve
from app.pipeline.rag import format_context, generate_answer, validate_hallucination, log_audit_entry
from app.models.schemas import RAGQueryIn, RAGAnswerOut, RAGSourceChunk
from app.config import settings

DEMO_QUERIES = [
    {"question": "What is the KYC status and expiry for this customer?", "persona": "internal"},
    {"question": "Is this customer a PEP and what sanctions list checks have been performed?", "persona": "internal"},
    {"question": "What is the confidence score for this golden record and which source systems contributed?", "persona": "internal"},
    {"question": "What is my account status and when was my last KYC verification?", "persona": "customer"},
    {"question": "Are there any compliance concerns with this customer based on their risk profile?", "persona": "internal"},
]


def run_rag_query(query: RAGQueryIn, db: Session) -> RAGAnswerOut:
    t0 = time.time()
    entity_id = str(query.entity_id) if query.entity_id else None

    chunks = retrieve(query.question, entity_id, query.persona, db, top_k=query.top_k)

    if not chunks:
        return RAGAnswerOut(
            answer="No relevant records found for your query.",
            sources=[],
            entity_id=query.entity_id,
            hallucination_check_passed=True,
            confidence=0.0,
            tokens_used=0,
            latency_ms=int((time.time() - t0) * 1000),
        )

    context = format_context(chunks, query.persona)
    gen_result = generate_answer(query.question, context, query.persona)
    hallucination = validate_hallucination(gen_result["answer"], context)

    sources = [
        RAGSourceChunk(
            chunk_id=uuid.UUID(c["id"]) if len(c["id"]) == 36 else uuid.uuid4(),
            chunk_type=c["chunk_type"],
            content_preview=c["content"][:200],
            similarity_score=c.get("similarity_score", 0.0),
            entity_id=uuid.UUID(c["customer_id"]) if len(c.get("customer_id", "")) == 36 else uuid.uuid4(),
        )
        for c in chunks
    ]

    avg_sim = sum(c.get("similarity_score", 0) for c in chunks) / max(len(chunks), 1)
    confidence = avg_sim if not hallucination["hallucination_detected"] else avg_sim * 0.5

    elapsed_ms = int((time.time() - t0) * 1000)
    query_id = str(uuid.uuid4())

    try:
        log_audit_entry(
            db=db,
            query_id=query_id,
            question=query.question,
            answer=gen_result["answer"],
            entity_id=entity_id,
            sources=[{"id": s.chunk_id, "chunk_type": s.chunk_type} for s in sources],
            hallucination_result=hallucination,
            persona=query.persona,
            tokens_used=gen_result["tokens_used"],
            latency_ms=elapsed_ms,
        )
    except Exception:
        pass

    return RAGAnswerOut(
        answer=gen_result["answer"],
        sources=sources,
        entity_id=query.entity_id,
        hallucination_check_passed=not hallucination["hallucination_detected"],
        confidence=round(confidence, 4),
        tokens_used=gen_result["tokens_used"],
        latency_ms=elapsed_ms,
    )
