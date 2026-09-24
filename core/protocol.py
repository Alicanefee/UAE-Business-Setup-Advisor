"""Source-bound agent protocol.

Agents never return free-form data. They return an AgentResult holding a list
of Claims, and every Claim carries a SourceRef: the canonical database row it
came from plus a SHA-256 hash of that row's content at retrieval time. A claim
cannot be constructed without a source, and the Verifier rejects any source
that does not exist, has changed, or is not in force.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    LAW = "law"
    DOCUMENT = "document"
    PENALTY = "penalty"
    ALTERNATIVE = "alternative"
    INSTITUTION = "institution"
    RULE = "rule"


def content_hash(row: dict, fields: list[str]) -> str:
    """Hash the canonical fields of a row. Field order is fixed per source type."""
    content = "|".join(str(row.get(f, "")) for f in fields)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SourceRef(BaseModel):
    """The canonical row a piece of information came from, plus its content hash."""

    type: SourceType
    id: str
    hash: str
    retrieved_at: datetime
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None

    @classmethod
    def from_row(cls, type_: SourceType, row: dict, canonical: list[str]) -> SourceRef:
        return cls(
            type=type_,
            id=str(row["id"]),
            hash=content_hash(row, canonical),
            retrieved_at=datetime.now(timezone.utc),
            effective_from=row.get("effective_from"),
            effective_to=row.get("effective_to"),
        )

    @property
    def key(self) -> str:
        return f"{self.type.value}:{self.id}"


class Claim(BaseModel):
    """A single verifiable piece of information. A claim without a source cannot exist."""

    slot: str  # template slot, e.g. "biz.type" or "documents"
    value: Any
    source: SourceRef
    confidence: float = Field(ge=0.0, le=1.0)


class AgentResult(BaseModel):
    agent: str
    status: Literal["ok", "need_info", "abstain"]
    claims: list[Claim] = Field(default_factory=list)
    question: Optional[str] = None  # template key, e.g. "location"
    question_source: Optional[SourceRef] = None
    reason: Optional[str] = None

    @classmethod
    def ok(cls, agent: str, claims: list[Claim]) -> AgentResult:
        if not claims:
            raise ValueError("An ok result cannot have an empty claim list")
        return cls(agent=agent, status="ok", claims=claims)

    @classmethod
    def need_info(cls, agent: str, question: str, source: SourceRef) -> AgentResult:
        if source is None:
            raise ValueError("A question cannot be asked without a source")
        return cls(agent=agent, status="need_info", question=question, question_source=source)

    @classmethod
    def abstain(cls, agent: str, reason: str) -> AgentResult:
        return cls(agent=agent, status="abstain", reason=reason)
