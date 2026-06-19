from __future__ import annotations
import enum
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class KYCStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class RiskRating(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceSystem(str, enum.Enum):
    CRM = "CRM"
    KYC = "KYC"
    CBS = "CBS"
    RISK = "RISK"


class ChunkType(str, enum.Enum):
    identity = "identity"
    contact = "contact"
    kyc_compliance = "kyc_compliance"
    risk_profile = "risk_profile"
    sanctions_pep = "sanctions_pep"
    customer_lifecycle = "customer_lifecycle"
    confidence_metadata = "confidence_metadata"


class SurvivorshipRule(str, enum.Enum):
    HIGHEST_TRUST = "HIGHEST_TRUST"
    MOST_RECENT = "MOST_RECENT"
    REGULATORY_LOCK = "REGULATORY_LOCK"
    MOST_COMPLETE = "MOST_COMPLETE"


# ─── Customer Schemas ─────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    nationality: Optional[str] = None


class GoldenRecordOut(CustomerBase):
    customer_id: UUID
    full_legal_name: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    kyc_status: Optional[str] = None
    risk_rating: Optional[str] = None
    is_pep: bool = False
    is_sanctioned: bool = False
    pep_type: Optional[str] = None
    kyc_verified_at: Optional[datetime] = None
    kyc_expiry_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source_count: int = 1

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "first_name": "John",
                "last_name": "Smith",
                "full_legal_name": "John A. Smith",
                "confidence_score": 0.94,
                "kyc_status": "VERIFIED",
                "risk_rating": "LOW",
                "is_pep": False,
                "is_sanctioned": False,
                "source_count": 3,
            }
        },
    }


class GoldenRecordList(BaseModel):
    items: list[GoldenRecordOut]
    total: int
    page: int
    page_size: int


# ─── Lineage Schemas ──────────────────────────────────────────────────────────

class AttributeLineageOut(BaseModel):
    attribute_name: str
    winning_value: Optional[str] = None
    winning_source: Optional[str] = None
    survivorship_rule: Optional[str] = None
    confidence: float = 0.0
    is_regulatory_lock: bool = False
    competing_sources: list[dict] = []
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GoldenRecordWithLineage(GoldenRecordOut):
    lineage: list[AttributeLineageOut] = []


# ─── Stewardship Schemas ──────────────────────────────────────────────────────

class MatchPairOut(BaseModel):
    pair_id: UUID
    record_a_id: str
    record_b_id: str
    source_a: Optional[str] = None
    source_b: Optional[str] = None
    match_probability: float
    match_features: dict = {}
    status: str = "pending"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MatchDecisionIn(BaseModel):
    pair_id: UUID
    decision: Literal["approved", "rejected"]
    reviewer_notes: Optional[str] = None


# ─── RAG Schemas ──────────────────────────────────────────────────────────────

class RAGQueryIn(BaseModel):
    question: str = Field(max_length=500)
    entity_id: Optional[UUID] = None
    persona: Literal["internal", "customer"] = "internal"
    top_k: int = Field(default=5, ge=1, le=20)

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Show me all PEP customers with expired KYC",
                "persona": "internal",
                "top_k": 5,
            }
        }
    }


class RAGSourceChunk(BaseModel):
    chunk_id: UUID
    chunk_type: str
    content_preview: str
    similarity_score: float
    entity_id: UUID


class RAGAnswerOut(BaseModel):
    answer: str
    sources: list[RAGSourceChunk]
    entity_id: Optional[UUID] = None
    hallucination_check_passed: bool
    confidence: float
    tokens_used: int
    latency_ms: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "answer": "The customer John Smith has VERIFIED KYC status expiring on 2026-12-01.",
                "sources": [],
                "hallucination_check_passed": True,
                "confidence": 0.91,
                "tokens_used": 320,
                "latency_ms": 1250,
            }
        }
    }


class RAGAuditLog(BaseModel):
    query_id: UUID
    question: str
    answer: str
    entity_id: Optional[UUID] = None
    hallucination_passed: bool
    persona: str
    sources_used: int
    tokens_used: int
    latency_ms: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── GDPR Schemas ─────────────────────────────────────────────────────────────

class ErasureRequestIn(BaseModel):
    customer_id: UUID
    requester_email: str
    reason: str


class ErasureStatusOut(BaseModel):
    request_id: UUID
    customer_id: UUID
    status: Literal["pending", "processing", "completed", "failed"]
    records_deleted: Optional[int] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── DQ Schemas ───────────────────────────────────────────────────────────────

class DQRuleResult(BaseModel):
    rule_name: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: Optional[str] = None


class DQReportOut(BaseModel):
    source_id: str
    source_system: str
    overall_score: float
    rules: list[DQRuleResult]
    checked_at: datetime
