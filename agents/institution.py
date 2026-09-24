"""Institution agent: (emirate, structure) → where to apply."""
from __future__ import annotations

from agents.base import Agent
from core.protocol import AgentResult, SourceType


class InstitutionAgent(Agent):
    name = "institution"

    def run(self, emirate: str, biz_type: str) -> AgentResult:
        rows = self.repo.institutions_for(emirate, biz_type)
        if not rows:
            return AgentResult.abstain(self.name, f"no_institution:{emirate}/{biz_type}")
        return AgentResult.ok(self.name, [
            self.claim("institutions", {
                "name": r["name"],
                "address": r.get("address") or "",
                "website": r.get("website") or "",
            }, SourceType.INSTITUTION, r)
            for r in rows
        ])
