"""Abstention policy: decide whether the collected results are strong enough
to compose an answer, or whether the case must go to a human expert."""
from __future__ import annotations

import yaml

from core.protocol import AgentResult, SourceType


class AbstentionPolicy:
    def __init__(self, repo):
        row = repo.fetch_source(SourceType.RULE, "abstention")
        if row is None:
            raise RuntimeError("Abstention policy missing from the rules table")
        self.policy = yaml.safe_load(row["body"])

    def evaluate(self, results: list[AgentResult]) -> tuple[bool, str]:
        """Return (should_abstain, reason)."""
        if not results:
            return True, "no_results"
        if any(r.status == "abstain" for r in results):
            return True, "agent_abstained"

        claims = [c for r in results for c in r.claims]
        min_conf = min((c.confidence for c in claims), default=0.0)
        if min_conf < self.policy["min_confidence"]:
            return True, f"low_confidence:{min_conf:.2f}"

        slots = {c.slot for c in claims}
        missing = [s for s in self.policy["mandatory_slots"] if s not in slots]
        if missing:
            return True, "missing_mandatory:" + ",".join(missing)

        return False, ""
