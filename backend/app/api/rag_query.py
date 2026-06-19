"""RAG query API endpoints."""
from __future__ import annotations
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.db_models import RAGAuditLog, GoldenRecord
from app.models.schemas import RAGQueryIn, RAGAnswerOut, RAGAuditLog as RAGAuditLogSchema
from app.pipeline.query_pipeline import run_rag_query

router = APIRouter(prefix="/rag", tags=["RAG Query"])


@router.post("/query", response_model=RAGAnswerOut)
async def rag_query(
    query: RAGQueryIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import Session
    from app.database import SyncSessionLocal

    def _run():
        with SyncSessionLocal() as sync_db:
            return run_rag_query(query, sync_db)

    result = await run_in_threadpool(_run)
    return result


@router.post("/demo", response_model=RAGAnswerOut)
async def rag_demo(body: dict, db: AsyncSession = Depends(get_db)):
    question = body.get("question", "What is the compliance status of this customer?")
    row = (await db.execute(
        select(GoldenRecord)
        .where(GoldenRecord.is_pep == True, GoldenRecord.kyc_status == "VERIFIED")
        .limit(1)
    )).scalar_one_or_none()

    entity_id = UUID(row.customer_id) if row else None
    query = RAGQueryIn(question=question, entity_id=entity_id, persona="internal")

    from app.database import SyncSessionLocal

    def _run():
        with SyncSessionLocal() as sync_db:
            return run_rag_query(query, sync_db)

    return await run_in_threadpool(_run)


@router.get("/history", response_model=list[RAGAuditLogSchema])
async def rag_history(
    entity_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(RAGAuditLog).order_by(RAGAuditLog.created_at.desc()).limit(limit)
    if entity_id:
        q = q.where(RAGAuditLog.customer_id == str(entity_id))
    rows = (await db.execute(q)).scalars().all()
    return [
        RAGAuditLogSchema(
            query_id=UUID(r.query_id) if r.query_id else uuid.uuid4(),
            question=r.question,
            answer=r.answer,
            entity_id=UUID(r.customer_id) if r.customer_id else None,
            hallucination_passed=bool(r.hallucination_passed),
            persona=r.persona or "internal",
            sources_used=r.sources_used or 0,
            tokens_used=r.tokens_used or 0,
            latency_ms=r.latency_ms or 0,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/stats")
async def rag_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(RAGAuditLog))).scalar_one()
    hall_failed = (await db.execute(
        select(func.count()).where(RAGAuditLog.hallucination_passed == False)
    )).scalar_one()
    hall_rate = hall_failed / max(total, 1)

    avg_lat = (await db.execute(select(func.avg(RAGAuditLog.latency_ms)))).scalar_one() or 0.0

    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    last24 = (await db.execute(
        select(func.count()).where(RAGAuditLog.created_at >= cutoff)
    )).scalar_one()

    return {
        "total_queries": total,
        "hallucination_rate": round(float(hall_rate), 4),
        "avg_latency_ms": round(float(avg_lat), 1),
        "queries_last_24h": last24,
        "top_chunk_types_retrieved": [],
    }
