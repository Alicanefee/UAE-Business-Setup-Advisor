"""Classifier: free text → legal structure + activity code.

Deterministic keyword extraction and structure rules come first. An optional
LLM extractor is used only as a fallback for signals the keywords missed, and
its output is accepted only if it falls inside the fixed vocabularies. The LLM
never writes text the user sees.
"""
from __future__ import annotations

from agents.base import Agent, find_keyword
from core.protocol import AgentResult, Claim


class ClassifierAgent(Agent):
    name = "classifier"

    def __init__(self, repo, llm=None):
        super().__init__(repo)
        self.llm = llm

    def run(self, text: str) -> AgentResult:
        cfg, src = self.rule("classifier")

        explicit_type = find_keyword(text, cfg["explicit_types"])
        activity = find_keyword(text, cfg["activities"])
        market = find_keyword(text, cfg["target_markets"])
        signal_conf = 1.0

        if self.llm and (activity is None or (market is None and explicit_type is None)):
            guess = self.llm.extract(text, {
                "activity": list(cfg["activities"]),
                "target_market": list(cfg["target_markets"]),
            })
            if activity is None and guess.get("activity"):
                activity, signal_conf = guess["activity"], cfg["llm_confidence"]
            if market is None and guess.get("target_market"):
                market, signal_conf = guess["target_market"], cfg["llm_confidence"]

        if activity is None:
            key = "describe_business" if explicit_type is None and market is None else "activity"
            return AgentResult.need_info(self.name, key, src)

        biz_type, type_conf = self._decide(cfg, explicit_type, activity, market)
        if biz_type is None:
            key = "target_market" if market is None else "structure"
            return AgentResult.need_info(self.name, key, src)

        conf = min(type_conf, signal_conf)
        return AgentResult.ok(self.name, [
            Claim(slot="biz.type", value=biz_type, source=src, confidence=conf),
            Claim(slot="biz.activity", value=activity, source=src, confidence=conf),
        ])

    @staticmethod
    def _decide(cfg: dict, explicit_type: str | None, activity: str,
                market: str | None) -> tuple[str | None, float]:
        # The user's stated structure wins over inferred rules.
        if explicit_type:
            return explicit_type, cfg["explicit_confidence"]
        signals = {"activity": activity, "target_market": market}
        for rule in cfg["rules"]:
            if all(signals.get(k) in allowed for k, allowed in rule["when"].items()):
                return rule["then"], rule["confidence"]
        return None, 0.0
