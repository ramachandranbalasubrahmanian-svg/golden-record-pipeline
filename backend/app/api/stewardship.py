"""Stewardship API — human review queue for entity resolution decisions."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update

from app.database import get_db
from app.models.db_models import MatchPair, SourceRecord, StewardshipQueue, EntityCluster
from app.models.schemas import MatchPairOut, MatchDecisionIn

router = APIRouter(prefix="/stewardship", tags=["Data Stewardship"])


def _pair_to_dict(pair: MatchPair) -> dict:
    return {
        "pair_id": pair.id,
        "record_a_id": pair.record_a_id,
        "record_b_id": pair.record_b_id,
        "source_a": None,
        "source_b": None,
        "match_probability": float(pair.match_probability or 0),
        "match_features": pair.match_features or {},
        "status": pair.status,
        "created_at": pair.created_at,
    }


@router.get("/queue")
async def stewardship_queue(
    status: str = "pending",
    priority: Optional[int] = None,
    source_a: Optional[str] = None,
    source_b: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "match_probability",
    db: AsyncSession = Depends(get_db),
):
    filters = [MatchPair.status == status]
    total = (await db.execute(
        select(func.count()).select_from(MatchPair).where(and_(*filters))
    )).scalar_one()

    pending_count = (await db.execute(
        select(func.count()).where(MatchPair.status == "pending")
    )).scalar_one()

    rows = (await db.execute(
        select(MatchPair)
        .where(and_(*filters))
        .order_by(MatchPair.match_probability.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    items = []
    for pair in rows:
        d = _pair_to_dict(pair)
        ra = (await db.execute(
            select(SourceRecord).where(SourceRecord.id == pair.record_a_id)
        )).scalar_one_or_none()
        rb = (await db.execute(
            select(SourceRecord).where(SourceRecord.id == pair.record_b_id)
        )).scalar_one_or_none()
        if ra:
            d["source_a"] = ra.source_system
            d["record_a"] = {"first_name": ra.first_name, "last_name": ra.last_name,
                             "email": ra.email, "phone": ra.phone, "source_system": ra.source_system}
        if rb:
            d["source_b"] = rb.source_system
            d["record_b"] = {"first_name": rb.first_name, "last_name": rb.last_name,
                             "email": rb.email, "phone": rb.phone, "source_system": rb.source_system}
        items.append(d)

    return {"items": items, "total": total, "pending_count": pending_count}


@router.post("/decide")
async def stewardship_decide(decision: MatchDecisionIn, db: AsyncSession = Depends(get_db)):
    pair = (await db.execute(
        select(MatchPair).where(MatchPair.id == str(decision.pair_id))
    )).scalar_one_or_none()
    if not pair:
        raise HTTPException(404, "Match pair not found")

    pair.status = decision.decision
    pair.reviewer_notes = decision.reviewer_notes
    pair.reviewed_at = datetime.utcnow()
    await db.commit()

    sq = (await db.execute(
        select(StewardshipQueue).where(StewardshipQueue.pair_id == str(decision.pair_id))
    )).scalar_one_or_none()
    if sq:
        sq.status = "resolved"
        await db.commit()

    return {"success": True, "pair_id": decision.pair_id, "action_taken": decision.decision}


@router.get("/stats")
async def stewardship_stats(db: AsyncSession = Depends(get_db)):
    total_pending = (await db.execute(
        select(func.count()).where(MatchPair.status == "pending")
    )).scalar_one()

    from datetime import timedelta
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    approved_today = (await db.execute(
        select(func.count()).where(
            MatchPair.status == "approved", MatchPair.reviewed_at >= today
        )
    )).scalar_one()
    rejected_today = (await db.execute(
        select(func.count()).where(
            MatchPair.status == "rejected", MatchPair.reviewed_at >= today
        )
    )).scalar_one()

    avg_prob = (await db.execute(
        select(func.avg(MatchPair.match_probability)).where(MatchPair.status == "pending")
    )).scalar_one() or 0.0

    auto_mergeable = (await db.execute(
        select(func.count()).where(MatchPair.match_probability >= 0.95)
    )).scalar_one()

    total_reviewed = (await db.execute(
        select(func.count()).where(MatchPair.status.in_(["approved", "rejected"]))
    )).scalar_one()
    total_all = (await db.execute(select(func.count()).select_from(MatchPair))).scalar_one()
    resolution_rate = total_reviewed / max(total_all, 1)

    return {
        "total_pending": total_pending,
        "total_approved_today": approved_today,
        "total_rejected_today": rejected_today,
        "avg_match_probability_pending": round(float(avg_prob), 4),
        "high_confidence_auto_mergeable": auto_mergeable,
        "resolution_rate": round(float(resolution_rate), 4),
        "top_conflict_sources": [],
    }


@router.get("/pair/{pair_id}/evidence")
async def pair_evidence(pair_id: UUID, db: AsyncSession = Depends(get_db)):
    pair = (await db.execute(
        select(MatchPair).where(MatchPair.id == str(pair_id))
    )).scalar_one_or_none()
    if not pair:
        raise HTTPException(404, "Pair not found")

    ra = (await db.execute(
        select(SourceRecord).where(SourceRecord.id == pair.record_a_id)
    )).scalar_one_or_none()
    rb = (await db.execute(
        select(SourceRecord).where(SourceRecord.id == pair.record_b_id)
    )).scalar_one_or_none()

    features = pair.match_features or {}
    breakdown = []
    for fname, score in features.items():
        s = float(score)
        interp = "Strong match" if s > 0.8 else ("Partial match" if s >= 0.5 else "Weak/no match")
        breakdown.append({"feature_name": fname, "score": s, "interpretation": interp})
    breakdown.sort(key=lambda x: x["score"], reverse=True)

    top_features = [b["feature_name"] for b in breakdown[:3] if b["score"] > 0.8]
    weak_features = [b["feature_name"] for b in breakdown[-3:] if b["score"] < 0.5]
    prob = float(pair.match_probability or 0)
    explanation = (
        f"These records have a {prob:.0%} match probability. "
        f"Strong signals: {', '.join(top_features) or 'none'}. "
        f"Weak signals: {', '.join(weak_features) or 'none'}."
    )

    return {
        "pair": _pair_to_dict(pair),
        "record_a": {c: getattr(ra, c, None) for c in ["first_name", "last_name", "email", "phone", "date_of_birth", "city", "source_system"]} if ra else {},
        "record_b": {c: getattr(rb, c, None) for c in ["first_name", "last_name", "email", "phone", "date_of_birth", "city", "source_system"]} if rb else {},
        "feature_breakdown": breakdown,
        "model_explanation": explanation,
        "similar_approved_pairs": [],
    }


@router.post("/auto-approve")
async def auto_approve(body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    threshold = float(body.get("threshold", 0.95))
    max_records = int(body.get("max_records", 1000))

    pairs = (await db.execute(
        select(MatchPair)
        .where(MatchPair.match_probability >= threshold, MatchPair.status == "pending")
        .limit(max_records)
    )).scalars().all()

    approved = 0
    errors = 0
    for pair in pairs:
        try:
            pair.status = "approved"
            pair.reviewed_at = datetime.utcnow()
            pair.reviewer_notes = "Auto-approved by system"
            approved += 1
        except Exception:
            errors += 1

    await db.commit()
    return {"approved": approved, "errors": errors, "clusters_updated": approved}
