"""Lineage tracker — saves and retrieves attribute-level lineage for golden records."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, func, text


def save_lineage(db: Session, customer_id: str, lineage_entries: list[dict]):
    from app.models.db_models import AttributeLineage
    for entry in lineage_entries:
        existing = db.execute(
            select(AttributeLineage).where(
                AttributeLineage.customer_id == customer_id,
                AttributeLineage.attribute_name == entry["attribute_name"],
            )
        ).scalar_one_or_none()

        if existing:
            existing.winning_value = entry.get("winning_value")
            existing.winning_source = entry.get("winning_source")
            existing.survivorship_rule = entry.get("survivorship_rule")
            existing.confidence = entry.get("confidence")
            existing.is_regulatory_lock = entry.get("is_regulatory_lock", False)
            existing.competing_sources = entry.get("competing_sources", [])
            existing.resolved_at = datetime.utcnow()
        else:
            db.add(AttributeLineage(
                customer_id=customer_id,
                attribute_name=entry["attribute_name"],
                winning_value=entry.get("winning_value"),
                winning_source=entry.get("winning_source"),
                survivorship_rule=entry.get("survivorship_rule"),
                confidence=entry.get("confidence"),
                is_regulatory_lock=entry.get("is_regulatory_lock", False),
                competing_sources=entry.get("competing_sources", []),
                resolved_at=datetime.utcnow(),
            ))
    db.commit()


def get_lineage(db: Session, customer_id: str) -> list[dict]:
    from app.models.db_models import AttributeLineage
    rows = db.execute(
        select(AttributeLineage)
        .where(AttributeLineage.customer_id == customer_id)
        .order_by(AttributeLineage.is_regulatory_lock.desc(), AttributeLineage.attribute_name)
    ).scalars().all()
    return [
        {
            "attribute_name": r.attribute_name,
            "winning_value": r.winning_value,
            "winning_source": r.winning_source,
            "survivorship_rule": r.survivorship_rule,
            "confidence": float(r.confidence or 0),
            "is_regulatory_lock": r.is_regulatory_lock,
            "competing_sources": r.competing_sources or [],
            "resolved_at": r.resolved_at,
        }
        for r in rows
    ]


def get_winning_source_summary(db: Session) -> dict:
    from app.models.db_models import AttributeLineage
    rows = db.execute(
        select(
            AttributeLineage.attribute_name,
            AttributeLineage.winning_source,
            func.count().label("win_count"),
        )
        .group_by(AttributeLineage.attribute_name, AttributeLineage.winning_source)
        .order_by(AttributeLineage.attribute_name)
    ).all()

    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        summary.setdefault(row.attribute_name, {})[row.winning_source or "UNKNOWN"] = row.win_count
    return summary
