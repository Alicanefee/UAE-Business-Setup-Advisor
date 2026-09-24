"""Hallucination harness: fabricated, tampered or expired sources must never
pass verification, and must never reach the user as an answer."""
from datetime import datetime, timezone

import pytest

from agents.document import DocumentAgent
from core.protocol import AgentResult, Claim, SourceRef, SourceType
from core.verifier import VerificationError, Verifier
from tests.conftest import TODAY, final_event


def _claim(repo, type_, id_, slot="laws.primary"):
    row = repo.fetch_source(type_, id_)
    src = SourceRef.from_row(type_, row, repo.canonical_fields(type_))
    return Claim(slot=slot, value=row.get("title") or row["id"], source=src, confidence=1.0)


def _verify(repo, claim):
    return Verifier(repo, today=lambda: TODAY).verify(AgentResult.ok("test", [claim]))


def test_valid_claim_passes(repo):
    assert _verify(repo, _claim(repo, SourceType.LAW, "L-FZ-DXB-001")).status == "ok"


def test_nonexistent_source_rejected(repo):
    fake = SourceRef(type=SourceType.LAW, id="L-INVENTED-001", hash="deadbeef",
                     retrieved_at=datetime.now(timezone.utc))
    claim = Claim(slot="laws.primary", value="Invented law", source=fake, confidence=1.0)
    with pytest.raises(VerificationError, match="not found"):
        _verify(repo, claim)


def test_forged_hash_rejected(repo):
    claim = _claim(repo, SourceType.LAW, "L-FZ-DXB-001")
    claim.source.hash = "0" * 64
    with pytest.raises(VerificationError, match="hash mismatch"):
        _verify(repo, claim)


def test_source_changed_after_retrieval_rejected(repo):
    claim = _claim(repo, SourceType.LAW, "L-FZ-DXB-001")
    repo.conn.execute("UPDATE laws SET body = body || ' (amended)' WHERE id = 'L-FZ-DXB-001'")
    with pytest.raises(VerificationError, match="hash mismatch"):
        _verify(repo, claim)


def test_expired_source_rejected(repo):
    repo.conn.execute("UPDATE laws SET effective_to = '2025-12-31' WHERE id = 'L-FZ-DXB-001'")
    claim = _claim(repo, SourceType.LAW, "L-FZ-DXB-001")
    with pytest.raises(VerificationError, match="expired"):
        _verify(repo, claim)


def test_not_yet_effective_source_rejected(repo):
    repo.conn.execute("UPDATE laws SET effective_from = '2027-01-01' WHERE id = 'L-FZ-DXB-001'")
    claim = _claim(repo, SourceType.LAW, "L-FZ-DXB-001")
    with pytest.raises(VerificationError, match="not yet in force"):
        _verify(repo, claim)


def test_forged_claim_never_reaches_the_user(orchestrator, monkeypatch):
    """An agent that returns a claim with a forged source makes the whole
    request abstain — no result event is produced."""
    real_run = DocumentAgent.run

    def forged_run(self, law_id):
        result = real_run(self, law_id)
        result.claims[0].value = {**result.claims[0].value, "name": "Invented Permit"}
        result.claims[0].source.hash = "f" * 64
        return result

    monkeypatch.setattr(DocumentAgent, "run", forged_run)
    event, states = final_event(orchestrator, "Software company in Dubai, clients overseas")
    assert event["type"] == "abstain"
    assert event["reason"].startswith("verification_failed")
    assert "compose" not in states
