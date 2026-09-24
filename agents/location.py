"""Location: free text → emirate."""
from __future__ import annotations

from agents.base import Agent, find_keyword
from core.protocol import AgentResult, Claim


class LocationAgent(Agent):
    name = "location"

    def run(self, text: str) -> AgentResult:
        cfg, src = self.rule("location")
        emirate = find_keyword(text, cfg["emirates"])
        if emirate is None:
            return AgentResult.need_info(self.name, "location", src)
        return AgentResult.ok(self.name, [
            Claim(slot="location.emirate", value=emirate, source=src,
                  confidence=cfg["confidence"]),
        ])
