"""GDPR endpoints — Right to Erasure (Article 17) and Data Portability (Article 20)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_

from app.database import get_db
from app.models.db_models import (
    GDPRErasureRequest, GoldenRecord, SourceRecord, AttributeLineage,
    RAGChunk, RAGAuditLog, Transaction, MatchPair, StewardshipQueue,
)
from app.models.schemas import ErasureRequestIn, ErasureStatusOut

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


async def _cascade_delete(customer_id: str, db: AsyncSession) -> int:
    deleted = 0

    # 1. rag_audit_log
    r = await db.execute(delete(RAGAuditLog).where(RAGAuditLog.customer_id == customer_id))
    deleted += r.rowcount

    # 2. rag_chunks
    r = await db.execute(delete(RAGChunk).where(RAGChunk.customer_id == customer_id))
    deleted += r.rowcount

    # 3. attribute_lineage
    r = await db.execute(delete(AttributeLineage).where(AttributeLineage.customer_id == customer_id))
    deleted += r.rowcount

    # 4. transactions
    r = await db.execute(delete(Transaction).where(Transaction.customer_id == customer_id))
    deleted += r.rowcount

    # 5. source records and related match pairs / stewardship queue
    src_rows = (await db.execute(
        select(SourceRecord.id).where(SourceRecord.external_id.contains(customer_id[:8]))
    )).scalars().all()
    src_ids = [str(s) for s in src_rows]

    if src_ids:
        for src_id in src_ids:
            pair_ids = (await db.execute(
                select(MatchPair.id).where(
                    (MatchPair.record_a_id == src_id) | (MatchPair.record_b_id == src_id)
                )
            )).scalars().all()
            for pid in pair_ids:
                await db.execute(delete(StewardshipQueue).where(StewardshipQueue.pair_id == str(pid)))
                deleted += 1
            await db.execute(delete(MatchPair).where(
                (MatchPair.record_a_id == src_id) | (MatchPair.record_b_id == src_id)
            ))
        await db.execute(delete(SourceRecord).where(SourceRecord.id.in_(src_ids)))
        deleted += len(src_ids)

    # 6. golden_record
    r = await db.execute(delete(GoldenRecord).where(GoldenRecord.customer_id == customer_id))
    deleted += r.rowcount

    await db.commit()
    return deleted


async def _run_erasure(request_id: str, customer_id: str, db: AsyncSession):
    req = (await db.execute(
        select(GDPRErasureRequest).where(GDPRErasureRequest.id == request_id)
    )).scalar_one_or_none()
    if not req:
        return
    req.status = "processing"
    await db.commit()
    try:
        n = await _cascade_delete(customer_id, db)
        req.status = "completed"
        req.records_deleted = n
        req.completed_at = datetime.utcnow()
    except Exception as e:
        req.status = "failed"
    await db.commit()


@router.post("/erasure-request", response_model=ErasureStatusOut, status_code=202)
async def erasure_request(
    body: ErasureRequestIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    cust = (await db.execute(
        select(GoldenRecord).where(GoldenRecord.customer_id == str(body.customer_id))
    )).scalar_one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")
    if cust.is_sanctioned:
        raise HTTPException(403, "Cannot erase sanctioned customer — regulatory hold")

    req = GDPRErasureRequest(
        customer_id=str(body.customer_id),
        requester_email=body.requester_email,
        reason=body.reason,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    background_tasks.add_task(_run_erasure, req.id, str(body.customer_id), db)

    return ErasureStatusOut(
        request_id=UUID(req.id),
        customer_id=body.customer_id,
        status="pending",
    )


@router.get("/erasure-status/{request_id}", response_model=ErasureStatusOut)
async def erasure_status(request_id: UUID, db: AsyncSession = Depends(get_db)):
    req = (await db.execute(
        select(GDPRErasureRequest).where(GDPRErasureRequest.id == str(request_id))
    )).scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Erasure request not found")
    return ErasureStatusOut(
        request_id=UUID(req.id),
        customer_id=UUID(req.customer_id),
        status=req.status,
        records_deleted=req.records_deleted,
        completed_at=req.completed_at,
    )


@router.post("/data-export/{customer_id}")
async def data_export(customer_id: UUID, db: AsyncSession = Depends(get_db)):
    cust = (await db.execute(
        select(GoldenRecord).where(GoldenRecord.customer_id == str(customer_id))
    )).scalar_one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")

    lineage_rows = (await db.execute(
        select(AttributeLineage).where(AttributeLineage.customer_id == str(customer_id))
    )).scalars().all()

    tx_count = (await db.execute(
        select(func.count()).where(Transaction.customer_id == str(customer_id))
    )).scalar_one()

    return {
        "customer_id": str(customer_id),
        "export_generated_at": datetime.utcnow().isoformat(),
        "profile": {
            "name": cust.full_legal_name,
            "date_of_birth": str(cust.date_of_birth),
            "email": cust.email,
            "phone": cust.phone,
            "address": cust.address_line1,
            "city": cust.city,
            "country": cust.country,
            "kyc_status": cust.kyc_status,
        },
        "data_sources": [
            {"attribute": l.attribute_name, "source": l.winning_source}
            for l in lineage_rows
        ],
        "transaction_summary": {
            "total_transactions": tx_count,
        },
    }


@router.get("/erasure-log")
async def erasure_log(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(GDPRErasureRequest).order_by(GDPRErasureRequest.requested_at.desc())
    if status:
        q = q.where(GDPRErasureRequest.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "request_id": r.id,
            "customer_id": r.customer_id,
            "requester_email": r.requester_email,
            "status": r.status,
            "records_deleted": r.records_deleted,
            "requested_at": r.requested_at,
            "completed_at": r.completed_at,
        }
        for r in rows
    ]
