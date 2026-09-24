from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.protocol import AgentResult, Claim, SourceRef, SourceType


def _src():
    return SourceRef(type=SourceType.RULE, id="classifier", hash="x",
                     retrieved_at=datetime.now(timezone.utc))


def test_ok_result_requires_claims():
    with pytest.raises(ValueError):
        AgentResult.ok("agent", [])


def test_question_requires_source():
    with pytest.raises(ValueError):
        AgentResult.need_info("agent", "location", None)


def test_claim_requires_source():
    with pytest.raises(ValidationError):
        Claim(slot="biz.type", value="freezone", confidence=0.9)


def test_confidence_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        Claim(slot="biz.type", value="freezone", source=_src(), confidence=1.5)


def test_source_hash_is_deterministic(repo):
    row = repo.fetch_source(SourceType.LAW, "L-FZ-DXB-001")
    fields = repo.canonical_fields(SourceType.LAW)
    a = SourceRef.from_row(SourceType.LAW, row, fields)
    b = SourceRef.from_row(SourceType.LAW, row, fields)
    assert a.hash == b.hash and a.key == "law:L-FZ-DXB-001"
