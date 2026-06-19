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


def generate_answer(question: str, context: str, persona: str, openai_client) -> dict:
    system_prompt = INTERNAL_PROMPT if persona == "internal" else CUSTOMER_PROMPT
    prompt = ANSWER_GENERATION_TEMPLATE.format(context=context, question=question)
    t0 = time.time()
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=800,
    )
    latency_ms = int((time.time() - t0) * 1000)
    answer = response.choices[0].message.content or ""
    tokens_used = response.usage.total_tokens if response.usage else 0
    return {"answer": answer, "tokens_used": tokens_used, "latency_ms": latency_ms}


def validate_hallucination(answer: str, context: str, openai_client) -> dict:
    prompt = HALLUCINATION_CHECK_TEMPLATE.format(context=context[:4000], answer=answer)
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw.strip())
        return {
            "hallucination_detected": bool(result.get("hallucination_detected", False)),
            "unsupported_claims": result.get("unsupported_claims", []),
            "confidence": float(result.get("confidence", 0.5)),
        }
    except Exception:
        return {"hallucination_detected": True, "unsupported_claims": [], "confidence": 0.5}


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
