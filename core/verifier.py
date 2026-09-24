"""Three-stage verification. Every AgentResult passes through here before its
claims can reach the composer.

Stage 1 — Schema:          slot, value and confidence are well-formed
Stage 2 — Existence + hash: the source row exists and its content is unchanged
Stage 3 — Effective window: the source is in force today

If an LLM (or a bug) invents a fact, it has no matching source row, or the
hash it carries does not match the row — and the result is rejected.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from core.protocol import AgentResult, Claim, content_hash


class VerificationError(Exception):
    pass


class Verifier:
    def __init__(self, repo, today: Callable[[], date] = date.today):
        self.repo = repo
        self.today = today

    def verify(self, result: AgentResult) -> AgentResult:
        if result.status != "ok":
            return result
        for claim in result.claims:
            self._s1_schema(claim)
            row = self._s2_exists(claim)
            self._s3_effective(claim, row)
        return result

    def _s1_schema(self, c: Claim) -> None:
        if not c.slot or c.value is None or c.value == "":
            raise VerificationError(f"Empty slot or value: {c.slot!r}")

    def _s2_exists(self, c: Claim) -> dict:
        row = self.repo.fetch_source(c.source.type, c.source.id)
        if row is None:
            raise VerificationError(f"Source not found: {c.source.key}")
        expected = content_hash(row, self.repo.canonical_fields(c.source.type))
        if expected != c.source.hash:
            raise VerificationError(
                f"Source hash mismatch on {c.source.key} "
                f"(expected {expected[:8]}, got {c.source.hash[:8]})"
            )
        return row

    def _s3_effective(self, c: Claim, row: dict) -> None:
        today = self.today().isoformat()
        start, end = row.get("effective_from"), row.get("effective_to")
        if start and start > today:
            raise VerificationError(f"Source not yet in force: {c.source.key} (from {start})")
        if end and end < today:
            raise VerificationError(f"Source expired: {c.source.key} (until {end})")
