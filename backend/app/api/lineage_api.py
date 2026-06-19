"""Lineage API endpoints."""
from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.db_models import AttributeLineage
from app.models.schemas import AttributeLineageOut

router = APIRouter(prefix="/lineage", tags=["Lineage"])


@router.get("/{customer_id}", response_model=list[AttributeLineageOut])
async def get_customer_lineage(customer_id: UUID, db: AsyncSession = Depends(get_db)):
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


@router.get("/source-wins/summary")
async def source_wins_summary(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(
            AttributeLineage.attribute_name,
            AttributeLineage.winning_source,
            func.count().label("win_count"),
        )
        .group_by(AttributeLineage.attribute_name, AttributeLineage.winning_source)
        .order_by(AttributeLineage.attribute_name)
    )).all()

    summary: dict = {}
    for row in rows:
        attr = row.attribute_name
        src = row.winning_source or "UNKNOWN"
        summary.setdefault(attr, {"CRM": 0, "KYC": 0, "CBS": 0, "RISK": 0})
        summary[attr][src] = summary[attr].get(src, 0) + row.win_count
    return summary


@router.get("/conflicts/active")
async def active_conflicts(
    customer_id: Optional[UUID] = None,
    attribute_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    filters = [AttributeLineage.competing_sources != None]
    if customer_id:
        filters.append(AttributeLineage.customer_id == str(customer_id))
    if attribute_name:
        filters.append(AttributeLineage.attribute_name == attribute_name)

    rows = (await db.execute(
        select(AttributeLineage).where(and_(*filters)).limit(500)
    )).scalars().all()

    result = []
    for r in rows:
        competing = r.competing_sources or []
        if competing:
            result.append({
                "customer_id": r.customer_id,
                "attribute_name": r.attribute_name,
                "winning_source": r.winning_source,
                "winning_value": r.winning_value,
                "competing_values": [
                    {"source": c.get("source"), "value": c.get("value")} for c in competing
                ],
            })
    return result
