"""Law router: (structure, emirate, activity) → governing license record."""
from __future__ import annotations

from datetime import date

from agents.base import Agent
from core.protocol import AgentResult, SourceType


class LawRouterAgent(Agent):
    name = "law_router"

    def run(self, biz_type: str, emirate: str, activity: str, on: date) -> AgentResult:
        laws = self.repo.find_laws(biz_type, emirate, activity, on)
        if not laws:
            return AgentResult.abstain(
                self.name, f"no_law_in_force:{biz_type}/{emirate}/{activity}"
            )
        primary = laws[0]
        return AgentResult.ok(self.name, [
            self.claim("laws.primary", primary["title"], SourceType.LAW, primary),
        ])
