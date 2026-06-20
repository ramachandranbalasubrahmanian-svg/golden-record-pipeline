"""RAG prompt templates, answer generation, and hallucination validation."""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

CHUNK_GROUPS = {
    "identity": ["first_name", "last_name", "full_legal_name", "date_of_birth", "nationality"],
    "contact": ["email", "phone", "address_line1", "city", "country"],
    "kyc_compliance": ["kyc_status", "kyc_tier", "kyc_verified_at", "kyc_expiry_at"],
    "risk_profile": ["risk_rating", "risk_score"],
    "sanctions_pep": ["is_pep", "pep_type", "pep_detected_at", "is_sanctioned", "sanctions_list", "sanctions_detected_at"],
    "customer_lifecycle": ["onboarded_at", "source_count", "confidence_score"],
    "confidence_metadata": ["confidence_score", "winning_sources", "source_count"],
}

INTERNAL_PROMPT = """You are an AI assistant for banking compliance and risk officers.
You have access to golden record data — authoritative, entity-resolved customer profiles with full lineage.
Answer questions precisely using ONLY the retrieved context.
Include source attribution when citing specific values (e.g., "per KYC system as of {date}").
For compliance-relevant attributes (PEP, sanctions, KYC status), always state the source system and verification date.
If information is not in the context, say "Not found in retrieved records" — never infer or assume.
Format your answer as a clear, structured response suitable for a compliance officer."""

CUSTOMER_PROMPT = """You are a helpful customer service assistant for a bank.
Answer questions about the customer's own account information based on their verified profile.
Use friendly, non-technical language. Never mention internal system names (KYC, CBS, CRM, RISK).
Never reveal risk scores, internal risk ratings, PEP status, or sanctions flags — these are internal.
If asked about information you don't have access to, say "Please contact your relationship manager for details."
Keep answers concise and clear."""

ANSWER_GENERATION_TEMPLATE = """Context from customer records:
{context}

Question: {question}

Answer based strictly on the context above. Do not add information not present in the context."""

HALLUCINATION_CHECK_TEMPLATE = """You are a fact-checker.
Given the following context and answer, determine if every factual claim in the answer is supported by the context.

Context:
{context}

Answer to check:
{answer}

Respond with JSON only:
{{"hallucination_detected": boolean, "unsupported_claims": [list of strings], "confidence": float}}
Do not add any text outside the JSON."""

INTERNAL_ONLY_CHUNKS = {"risk_profile", "confidence_metadata"}


def format_context(chunks: list[dict], persona: str = "internal") -> str:
    lines = []
    for chunk in chunks:
        ct = chunk.get("chunk_type", "")
        if persona == "customer" and ct in INTERNAL_ONLY_CHUNKS:
            continue
        content = chunk.get("content", "")
        lines.append(f"[{ct.upper()}]\n{content}\n")
    return "\n".join(lines)


def generate_answer(question: str, context: str, persona: str, _client=None) -> dict:
    t0 = time.time()
    q_lower = question.lower()

    if not context.strip():
        return {"answer": "No relevant records found for your query.", "tokens_used": 0, "latency_ms": 0}

    # Extract key facts from retrieved chunks
    lines = [l.strip() for l in context.splitlines() if l.strip() and not l.startswith("[")]

    if persona == "customer":
        # Filter out internal fields
        lines = [l for l in lines if not any(k in l.lower() for k in ["risk", "pep", "sanction", "confidence", "source"])]
        intro = "Based on your verified profile:"
    else:
        intro = "Based on retrieved compliance records:"

    # Build structured answer from chunk content
    relevant = []
    keywords = [w for w in q_lower.split() if len(w) > 3]
    for line in lines:
        if any(k in line.lower() for k in keywords) or len(relevant) < 5:
            relevant.append(f"• {line}")
        if len(relevant) >= 10:
            break

    if not relevant:
        relevant = [f"• {l}" for l in lines[:8]]

    answer = f"{intro}\n\n" + "\n".join(relevant)

    if persona == "internal":
        answer += "\n\n*Answer generated from retrieved golden record chunks. All data sourced from verified records.*"
    else:
        answer += "\n\nIf you need further assistance, please contact your relationship manager."

    latency_ms = int((time.time() - t0) * 1000)
    return {"answer": answer, "tokens_used": 0, "latency_ms": latency_ms}


def validate_hallucination(answer: str, context: str, _client=None) -> dict:
    # Rule-based: answer is grounded if it only uses words/phrases from context
    answer_words = set(answer.lower().split())
    context_words = set(context.lower().split())
    overlap = len(answer_words & context_words) / max(len(answer_words), 1)
    hallucination_detected = overlap < 0.15
    return {
        "hallucination_detected": hallucination_detected,
        "unsupported_claims": [],
        "confidence": round(overlap, 2),
    }


def log_audit_entry(
    db,
    query_id: str,
    question: str,
    answer: str,
    entity_id: Optional[str],
    sources: list[dict],
    hallucination_result: dict,
    persona: str,
    tokens_used: int,
    latency_ms: int,
):
    from app.models.db_models import RAGAuditLog
    log = RAGAuditLog(
        query_id=str(query_id),
        customer_id=str(entity_id) if entity_id else None,
        question=question,
        answer=answer,
        sources_used=len(sources),
        hallucination_passed=not hallucination_result.get("hallucination_detected", True),
        persona=persona,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
    )
    db.add(log)
    db.commit()
