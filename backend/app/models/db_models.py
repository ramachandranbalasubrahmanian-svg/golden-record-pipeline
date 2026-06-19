from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint, func, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False
    Vector = None


def _uuid_default():
    return str(uuid.uuid4())


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_system: Mapped[str] = mapped_column(String(20), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address_line1: Mapped[Optional[str]] = mapped_column(String(300))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(3))
    nationality: Mapped[Optional[str]] = mapped_column(String(3))
    kyc_status: Mapped[Optional[str]] = mapped_column(String(20))
    kyc_tier: Mapped[Optional[str]] = mapped_column(String(10))
    risk_rating: Mapped[Optional[str]] = mapped_column(String(10))
    is_pep: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sanctioned: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    dq_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    dq_report: Mapped[Optional[dict]] = mapped_column(JSONB)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_source_records_source_external", "source_system", "external_id"),
        Index("ix_source_records_last_name", "last_name"),
    )


class EntityCluster(Base):
    __tablename__ = "entity_clusters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    cluster_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    record_ids: Mapped[Optional[list]] = mapped_column(JSONB)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    match_method: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchPair(Base):
    __tablename__ = "match_pairs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    record_a_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("source_records.id"))
    record_b_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("source_records.id"))
    match_probability: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    match_features: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(100))
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_match_pairs_status", "status"),
    )


class GoldenRecord(Base):
    __tablename__ = "golden_records"

    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("entity_clusters.cluster_id"))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    full_legal_name: Mapped[Optional[str]] = mapped_column(String(200))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address_line1: Mapped[Optional[str]] = mapped_column(String(300))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(3))
    nationality: Mapped[Optional[str]] = mapped_column(String(3))
    kyc_status: Mapped[Optional[str]] = mapped_column(String(20))
    kyc_tier: Mapped[Optional[str]] = mapped_column(String(10))
    kyc_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    kyc_expiry_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    risk_rating: Mapped[Optional[str]] = mapped_column(String(10))
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 3))
    is_pep: Mapped[bool] = mapped_column(Boolean, default=False)
    pep_type: Mapped[Optional[str]] = mapped_column(String(50))
    pep_detected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_sanctioned: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctions_list: Mapped[Optional[str]] = mapped_column(String(100))
    sanctions_detected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    winning_sources: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lineage: Mapped[List["AttributeLineage"]] = relationship("AttributeLineage", back_populates="customer", cascade="all, delete-orphan")
    rag_chunks: Mapped[List["RAGChunk"]] = relationship("RAGChunk", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_golden_records_last_name", "last_name"),
        Index("ix_golden_records_kyc_status", "kyc_status"),
        Index("ix_golden_records_risk_rating", "risk_rating"),
        Index("ix_golden_records_is_pep", "is_pep"),
        Index("ix_golden_records_is_sanctioned", "is_sanctioned"),
    )


class AttributeLineage(Base):
    __tablename__ = "attribute_lineage"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("golden_records.customer_id", ondelete="CASCADE"))
    attribute_name: Mapped[str] = mapped_column(String(100), nullable=False)
    winning_value: Mapped[Optional[str]] = mapped_column(Text)
    winning_source: Mapped[Optional[str]] = mapped_column(String(20))
    survivorship_rule: Mapped[Optional[str]] = mapped_column(String(100))
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    is_regulatory_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    competing_sources: Mapped[Optional[list]] = mapped_column(JSONB)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["GoldenRecord"] = relationship("GoldenRecord", back_populates="lineage")

    __table_args__ = (
        UniqueConstraint("customer_id", "attribute_name", name="uq_lineage_customer_attribute"),
    )


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("golden_records.customer_id", ondelete="CASCADE"))
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    embedding = mapped_column(Vector(1536) if _HAS_PGVECTOR and Vector else Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["GoldenRecord"] = relationship("GoldenRecord", back_populates="rag_chunks")


class RAGAuditLog(Base):
    __tablename__ = "rag_audit_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    query_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    customer_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[Optional[int]] = mapped_column(Integer)
    hallucination_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    persona: Mapped[Optional[str]] = mapped_column(String(20))
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StewardshipQueue(Base):
    __tablename__ = "stewardship_queue"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    pair_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("match_pairs.id"))
    priority: Mapped[int] = mapped_column(Integer, default=5)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("golden_records.customer_id"))
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    transaction_type: Mapped[Optional[str]] = mapped_column(String(50))
    channel: Mapped[Optional[str]] = mapped_column(String(50))
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(200))
    counterparty_country: Mapped[Optional[str]] = mapped_column(String(3))
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    suspicious_reason: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_transactions_customer_date", "customer_id", "transaction_date"),
    )


class GDPRErasureRequest(Base):
    __tablename__ = "gdpr_erasure_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_default)
    customer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    records_deleted: Mapped[Optional[int]] = mapped_column(Integer)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
