"""Golden Records REST endpoints."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, and_, or_

from app.database import get_db
from app.models.db_models import GoldenRecord, AttributeLineage, Transaction
from app.models.schemas import GoldenRecordOut, GoldenRecordList, GoldenRecordWithLineage, AttributeLineageOut

router = APIRouter(prefix="/customers", tags=["Golden Records"])


def _gr_to_dict(row: GoldenRecord) -> dict:
    return {
        "customer_id": row.customer_id,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "full_legal_name": row.full_legal_name,
        "date_of_birth": row.date_of_birth,
        "email": row.email,
        "phone": row.phone,
        "address_line1": row.address_line1,
        "city": row.city,
        "country": row.country,
        "nationality": row.nationality,
        "confidence_score": float(row.confidence_score or 0),
        "kyc_status": row.kyc_status,
        "risk_rating": row.risk_rating,
        "is_pep": row.is_pep,
        "is_sanctioned": row.is_sanctioned,
        "pep_type": row.pep_type,
        "kyc_verified_at": row.kyc_verified_at,
        "kyc_expiry_at": row.kyc_expiry_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "source_count": row.source_count,
    }


@router.get("", response_model=GoldenRecordList)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_rating: Optional[str] = None,
    kyc_status: Optional[str] = None,
    is_pep: Optional[bool] = None,
    is_sanctioned: Optional[bool] = None,
    search: Optional[str] = None,
    country: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if risk_rating:
        filters.append(GoldenRecord.risk_rating == risk_rating.upper())
    if kyc_status:
        filters.append(GoldenRecord.kyc_status == kyc_status.upper())
    if is_pep is not None:
        filters.append(GoldenRecord.is_pep == is_pep)
    if is_sanctioned is not None:
        filters.append(GoldenRecord.is_sanctioned == is_sanctioned)
    if search:
        filters.append(GoldenRecord.full_legal_name.ilike(f"%{search}%"))
    if country:
        filters.append(GoldenRecord.country.ilike(country))

    count_q = select(func.count()).select_from(GoldenRecord)
    if filters:
        count_q = count_q.where(and_(*filters))
    total = (await db.execute(count_q)).scalar_one()

    sort_col = getattr(GoldenRecord, sort_by, GoldenRecord.updated_at)
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    q = select(GoldenRecord).order_by(order).offset((page - 1) * page_size).limit(page_size)
    if filters:
        q = q.where(and_(*filters))

    rows = (await db.execute(q)).scalars().all()
    items = [GoldenRecordOut(**_gr_to_dict(r)) for r in rows]
    return GoldenRecordList(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats/summary")
async def customer_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(GoldenRecord))).scalar_one()
    by_risk = {}
    for rating in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        cnt = (await db.execute(
            select(func.count()).where(GoldenRecord.risk_rating == rating)
        )).scalar_one()
        by_risk[rating] = cnt

    by_kyc = {}
    for status in ("VERIFIED", "PENDING", "FAILED", "EXPIRED"):
        cnt = (await db.execute(
            select(func.count()).where(GoldenRecord.kyc_status == status)
        )).scalar_one()
        by_kyc[status] = cnt

    pep_count = (await db.execute(
        select(func.count()).where(GoldenRecord.is_pep == True)
    )).scalar_one()
    sanctioned_count = (await db.execute(
        select(func.count()).where(GoldenRecord.is_sanctioned == True)
    )).scalar_one()

    avg_conf = (await db.execute(
        select(func.avg(GoldenRecord.confidence_score))
    )).scalar_one() or 0.0

    avg_src = (await db.execute(
        select(func.avg(GoldenRecord.source_count))
    )).scalar_one() or 0.0

    high_conf = (await db.execute(
        select(func.count()).where(GoldenRecord.confidence_score >= 0.85)
    )).scalar_one()

    multi_src = (await db.execute(
        select(func.count()).where(GoldenRecord.source_count >= 2)
    )).scalar_one()

    return {
        "total_customers": total,
        "by_risk_rating": by_risk,
        "by_kyc_status": by_kyc,
        "pep_count": pep_count,
        "sanctioned_count": sanctioned_count,
        "avg_confidence_score": round(float(avg_conf), 4),
        "avg_source_count": round(float(avg_src), 2),
        "high_confidence_pct": round(high_conf / max(total, 1), 4),
        "multi_source_pct": round(multi_src / max(total, 1), 4),
    }


@router.get("/at-risk/expiring-kyc", response_model=list[GoldenRecordOut])
async def expiring_kyc(days_ahead: int = 30, db: AsyncSession = Depends(get_db)):
    cutoff = datetime.utcnow() + timedelta(days=days_ahead)
    rows = (await db.execute(
        select(GoldenRecord)
        .where(
            GoldenRecord.kyc_expiry_at <= cutoff,
            GoldenRecord.kyc_expiry_at >= datetime.utcnow(),
        )
        .limit(200)
    )).scalars().all()
    return [GoldenRecordOut(**_gr_to_dict(r)) for r in rows]


@router.get("/{customer_id}", response_model=GoldenRecordOut)
async def get_customer(customer_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(GoldenRecord).where(GoldenRecord.customer_id == str(customer_id))
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Customer not found")
    return GoldenRecordOut(**_gr_to_dict(row))


@router.get("/{customer_id}/full", response_model=GoldenRecordWithLineage)
async def get_customer_full(customer_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(GoldenRecord).where(GoldenRecord.customer_id == str(customer_id))
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Customer not found")
    lineage_rows = (await db.execute(
        select(AttributeLineage)
        .where(AttributeLineage.customer_id == str(customer_id))
        .order_by(AttributeLineage.is_regulatory_lock.desc(), AttributeLineage.attribute_name)
    )).scalars().all()
    lineage = [
        AttributeLineageOut(
            attribute_name=l.attribute_name,
            winning_value=l.winning_value,
            winning_source=l.winning_source,
            survivorship_rule=l.survivorship_rule,
            confidence=float(l.confidence or 0),
            is_regulatory_lock=l.is_regulatory_lock,
            competing_sources=l.competing_sources or [],
            resolved_at=l.resolved_at,
        )
        for l in lineage_rows
    ]
    return GoldenRecordWithLineage(**_gr_to_dict(row), lineage=lineage)


@router.get("/{customer_id}/lineage", response_model=list[AttributeLineageOut])
async def get_lineage(customer_id: UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AttributeLineage)
        .where(AttributeLineage.customer_id == str(customer_id))
        .order_by(AttributeLineage.is_regulatory_lock.desc(), AttributeLineage.attribute_name)
    )).scalars().all()
    return [
        AttributeLineageOut(
            attribute_name=r.attribute_name,
            winning_value=r.winning_value,
            winning_source=r.winning_source,
            survivorship_rule=r.survivorship_rule,
            confidence=float(r.confidence or 0),
            is_regulatory_lock=r.is_regulatory_lock,
            competing_sources=r.competing_sources or [],
            resolved_at=r.resolved_at,
        )
        for r in rows
    ]


@router.get("/{customer_id}/transactions")
async def get_transactions(
    customer_id: UUID,
    page: int = 1,
    page_size: int = 20,
    is_suspicious: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = [Transaction.customer_id == str(customer_id)]
    if is_suspicious is not None:
        filters.append(Transaction.is_suspicious == is_suspicious)
    if start_date:
        filters.append(Transaction.transaction_date >= start_date)
    if end_date:
        filters.append(Transaction.transaction_date <= end_date)

    total = (await db.execute(
        select(func.count()).select_from(Transaction).where(and_(*filters))
    )).scalar_one()

    suspicious_count = (await db.execute(
        select(func.count()).select_from(Transaction).where(
            and_(Transaction.customer_id == str(customer_id), Transaction.is_suspicious == True)
        )
    )).scalar_one()

    rows = (await db.execute(
        select(Transaction)
        .where(and_(*filters))
        .order_by(Transaction.transaction_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = [
        {
            "id": r.id, "customer_id": r.customer_id,
            "transaction_date": r.transaction_date, "amount": float(r.amount),
            "currency": r.currency, "transaction_type": r.transaction_type,
            "channel": r.channel, "counterparty_name": r.counterparty_name,
            "counterparty_country": r.counterparty_country,
            "is_suspicious": r.is_suspicious, "suspicious_reason": r.suspicious_reason,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "suspicious_count": suspicious_count}
