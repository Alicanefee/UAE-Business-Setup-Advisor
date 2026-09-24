"""Shared helpers for agents.

Agents are deterministic: they read canonical rows from the repository and
wrap each fact in a Claim bound to that row. Rule-driven agents load their
configuration from the `rules` table, so the rules they apply are exactly the
rules they cite.
"""
from __future__ import annotations

import re

import yaml

from core.protocol import Claim, SourceRef, SourceType


class Agent:
    name = "agent"

    def __init__(self, repo):
        self.repo = repo

    def source(self, type_: SourceType, row: dict) -> SourceRef:
        return SourceRef.from_row(type_, row, self.repo.canonical_fields(type_))

    def claim(self, slot: str, value, type_: SourceType, row: dict,
              confidence: float = 1.0) -> Claim:
        return Claim(slot=slot, value=value, source=self.source(type_, row),
                     confidence=confidence)

    def rule(self, rule_id: str) -> tuple[dict, SourceRef]:
        """Load a rule set and the SourceRef that cites it."""
        row = self.repo.fetch_source(SourceType.RULE, rule_id)
        if row is None:
            raise RuntimeError(f"Rule set '{rule_id}' missing from the rules table")
        return yaml.safe_load(row["body"]), self.source(SourceType.RULE, row)


def find_keyword(text: str, vocabulary: dict[str, list[str]]) -> str | None:
    """Return the first vocabulary key with a keyword present in `text` as a whole word."""
    lowered = text.lower()
    for key, keywords in vocabulary.items():
        for kw in keywords:
            if re.search(r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)", lowered):
                return key
    return None
