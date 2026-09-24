"""Document agent: governing license → required documents."""
from __future__ import annotations

from agents.base import Agent
from core.protocol import AgentResult, SourceType


def document_value(d: dict) -> dict:
    return {
        "name": d["name"],
        "issuer": d.get("issuer") or "the applicant",
        "how_to_obtain": d.get("how_to_obtain") or "",
        "requirement": "mandatory" if d.get("is_mandatory") else "optional",
        "notes": d.get("notes") or "",
    }


class DocumentAgent(Agent):
    name = "document"

    def run(self, law_id: str) -> AgentResult:
        docs = self.repo.documents_for_law(law_id)
        if not docs:
            return AgentResult.abstain(self.name, f"no_documents_for_law:{law_id}")
        return AgentResult.ok(self.name, [
            self.claim("documents", document_value(d), SourceType.DOCUMENT, d) for d in docs
        ])
