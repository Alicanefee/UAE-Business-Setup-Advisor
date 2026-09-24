"""Renewal agents: document check, penalties and alternative documents."""
from __future__ import annotations

import re
from datetime import date

from agents.base import Agent
from agents.document import document_value
from core.protocol import AgentResult, Claim, SourceType


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


class RenewalCheckAgent(Agent):
    """Compares the documents the user holds with those the license requires."""

    name = "renewal_check"

    def run(self, law_id: str, held: list[str]) -> AgentResult:
        cfg, _ = self.rule("renewal")
        required = [d for d in self.repo.documents_for_law(law_id)
                    if d["is_mandatory"] or cfg["report_optional_as_missing"]]
        if not required:
            return AgentResult.abstain(self.name, f"no_required_documents:{law_id}")

        held_norm = [h for h in (_normalize(x) for x in held) if len(h) >= cfg["min_match_length"]]
        claims: list[Claim] = []
        for d in required:
            name = _normalize(d["name"])
            matched = any(h in name or name in h for h in held_norm)
            slot = "renewal.matched" if matched else "renewal.missing"
            claims.append(self.claim(slot, document_value(d), SourceType.DOCUMENT, d,
                                     confidence=cfg["confidence"]))
        return AgentResult.ok(self.name, claims)


class PenaltyAgent(Agent):
    name = "penalty"

    def run(self, law_id: str, on: date) -> AgentResult:
        rows = self.repo.penalties_for_law(law_id, on)
        if not rows:
            return AgentResult.abstain(self.name, f"no_penalty_record:{law_id}")
        return AgentResult.ok(self.name, [
            self.claim("penalties", {
                "condition": r["condition"],
                "amount": _format_amount(r.get("amount_aed")),
                "note": r.get("note") or "",
            }, SourceType.PENALTY, r)
            for r in rows
        ])


class AlternativeAgent(Agent):
    name = "alternative"

    def run(self, missing_docs: list[str], on: date) -> AgentResult:
        rows = self.repo.alternatives_for(missing_docs, on)
        if not rows:
            return AgentResult.abstain(self.name, "no_alternative_record")
        return AgentResult.ok(self.name, [
            self.claim("alternatives", {
                "missing_doc": r["missing_doc"],
                "alternative_doc": r["alternative_doc"],
                "conditions": r.get("conditions") or "",
            }, SourceType.ALTERNATIVE, r)
            for r in rows
        ])


def _format_amount(amount: str | None) -> str:
    if not amount:
        return "amount not recorded"
    return f"AED {amount}" if amount[0].isdigit() else amount
