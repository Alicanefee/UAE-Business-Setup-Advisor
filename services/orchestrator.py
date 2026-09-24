"""Orchestrator: drives the agents through the explicit state machine.

`stream()` yields one event per state plus exactly one terminal event:
  {"type": "question", ...}  more information is needed from the user
  {"type": "result", ...}    a composed, fully sourced answer
  {"type": "abstain", ...}   the case was escalated to a human expert

Every agent result is verified before its claims are used. A verification
failure is never shown to the user as an answer — it becomes an abstention.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Callable, Iterator

from agents.classifier import ClassifierAgent
from agents.document import DocumentAgent
from agents.institution import InstitutionAgent
from agents.law_router import LawRouterAgent
from agents.location import LocationAgent
from agents.renewal import AlternativeAgent, PenaltyAgent, RenewalCheckAgent
from core.abstention import AbstentionPolicy
from core.fsm import State, transition
from core.protocol import AgentResult
from core.settings import DEFAULT_LOCALE, RECORDS_DIR
from core.verifier import VerificationError, Verifier
from services.composer import Composer
from services.escalation import escalate
from storage.session import Session, SessionStore

log = logging.getLogger(__name__)

FACT_SLOTS = {"biz.type", "biz.activity", "location.emirate", "laws.primary"}
ACTIVITY_QUESTIONS = {"describe_business", "activity"}


class Orchestrator:
    def __init__(self, repo, llm=None, sessions: SessionStore | None = None,
                 records_dir: Path = RECORDS_DIR, today: Callable[[], date] = date.today,
                 locale: str = DEFAULT_LOCALE):
        self.repo = repo
        self.sessions = sessions or SessionStore()
        self.records_dir = records_dir
        self.today = today
        self.locale = locale
        self.verifier = Verifier(repo, today)
        self.policy = AbstentionPolicy(repo)
        self.classifier = ClassifierAgent(repo, llm)
        self.location = LocationAgent(repo)
        self.law_router = LawRouterAgent(repo)
        self.documents = DocumentAgent(repo)
        self.institutions = InstitutionAgent(repo)
        self.renewal = RenewalCheckAgent(repo)
        self.penalties = PenaltyAgent(repo)
        self.alternatives = AlternativeAgent(repo)

    def stream(self, session_id: str, message: str = "", mode: str = "new",
               documents: list[str] | None = None) -> Iterator[dict]:
        s = self._prepare(session_id, message, mode, documents)
        composer = Composer(self.locale)
        today = self.today()
        results: list[AgentResult] = []
        pending: AgentResult | None = None
        reason = ""
        law_id = ""
        missing: list[str] = []

        state = State.START
        while state is not State.DONE:
            yield {"type": "state", "state": state.value}

            if state is State.START:
                state = transition(state, State.CLASSIFY)

            elif state is State.CLASSIFY:
                r = self._checked(self.classifier.run(s.text))
                if r.status == "need_info":
                    if r.question in ACTIVITY_QUESTIONS:
                        pending, state = r, transition(state, State.NEED_ACTIVITY)
                        continue
                    yield self._question(composer, r)
                    return
                if r.status == "abstain":
                    results.append(r)
                    reason, state = r.reason, transition(state, State.ABSTAIN)
                    continue
                results.append(r)
                self._absorb(s, r)

                r = self._checked(self.location.run(s.text))
                if r.status == "need_info":
                    pending, state = r, transition(state, State.NEED_LOCATION)
                    continue
                if r.status == "abstain":
                    results.append(r)
                    reason, state = r.reason, transition(state, State.ABSTAIN)
                    continue
                results.append(r)
                self._absorb(s, r)
                state = transition(state, State.ROUTE_LAW)

            elif state in (State.NEED_ACTIVITY, State.NEED_LOCATION):
                # The session waits here; the next message restarts classification.
                yield self._question(composer, pending)
                return

            elif state is State.ROUTE_LAW:
                r = self._checked(self.law_router.run(
                    s.facts["biz.type"], s.facts["location.emirate"],
                    s.facts["biz.activity"], today))
                results.append(r)
                if r.status != "ok":
                    reason, state = r.reason, transition(state, State.ABSTAIN)
                    continue
                self._absorb(s, r)
                law_id = r.claims[0].source.id
                state = transition(state, State.BRANCH)

            elif state is State.BRANCH:
                state = transition(state, State.RENEW_UPLOAD if s.is_renewal else State.NEW_DOCS)

            elif state is State.NEW_DOCS:
                r = self._checked(self.documents.run(law_id))
                results.append(r)
                if r.status != "ok":
                    reason, state = r.reason, transition(state, State.ABSTAIN)
                    continue
                state = transition(state, State.NEW_INSTITUTIONS)

            elif state is State.NEW_INSTITUTIONS:
                r = self._checked(self.institutions.run(s.facts["location.emirate"],
                                                        s.facts["biz.type"]))
                if r.status == "ok":  # optional section
                    results.append(r)
                state = transition(state, State.COMPOSE)

            elif state is State.RENEW_UPLOAD:
                if not s.held_documents:
                    _, src = self.renewal.rule("renewal")
                    yield self._question(composer, AgentResult.need_info(
                        self.renewal.name, "upload", src))
                    return
                state = transition(state, State.RENEW_COMPARE)

            elif state is State.RENEW_COMPARE:
                r = self._checked(self.renewal.run(law_id, s.held_documents))
                results.append(r)
                if r.status != "ok":
                    reason, state = r.reason, transition(state, State.ABSTAIN)
                    continue
                missing = [c.value["name"] for c in r.claims if c.slot == "renewal.missing"]
                state = transition(state, State.RENEW_PENALTY)

            elif state is State.RENEW_PENALTY:
                r = self._checked(self.penalties.run(law_id, today))
                if r.status == "ok":  # optional section
                    results.append(r)
                state = transition(state, State.RENEW_ALTERNATIVE)

            elif state is State.RENEW_ALTERNATIVE:
                if missing:
                    r = self._checked(self.alternatives.run(missing, today))
                    if r.status == "ok":  # optional section
                        results.append(r)
                state = transition(state, State.COMPOSE)

            elif state is State.COMPOSE:
                abstain, reason = self.policy.evaluate(results)
                if abstain:
                    state = transition(state, State.ABSTAIN)
                    continue
                claims = [c for r in results for c in r.claims]
                answer = composer.render("renewal" if s.is_renewal else "new", claims)
                yield {"type": "result", "answer": answer, "sources": answer["sources"]}
                s.completed = True
                state = transition(state, State.DONE)

            elif state is State.ABSTAIN:
                escalate(self.records_dir, s, reason, results)
                yield {"type": "abstain", "text": composer.abstain_text(), "reason": reason}
                s.completed = True
                state = transition(state, State.DONE)

    # ── helpers ──────────────────────────────────────────────────────────

    def _prepare(self, session_id: str, message: str, mode: str,
                 documents: list[str] | None) -> Session:
        s = self.sessions.get_or_create(session_id)
        if s.completed:  # a finished conversation starts a fresh request
            s.text, s.held_documents, s.completed = "", [], False
        if message.strip():
            s.text = f"{s.text} {message.strip()}".strip()
        s.is_renewal = mode == "renew"
        if documents:
            s.held_documents = [d.strip() for d in documents if d.strip()]
        s.facts = {}
        return s

    def _checked(self, result: AgentResult) -> AgentResult:
        try:
            return self.verifier.verify(result)
        except VerificationError as exc:
            log.warning("Verification failed for %s: %s", result.agent, exc)
            return AgentResult.abstain(result.agent, f"verification_failed: {exc}")

    @staticmethod
    def _absorb(s: Session, r: AgentResult) -> None:
        for c in r.claims:
            if c.slot in FACT_SLOTS:
                s.facts.setdefault(c.slot, c.value)

    @staticmethod
    def _question(composer: Composer, r: AgentResult) -> dict:
        return {"type": "question", "key": r.question, "text": composer.question(r.question),
                "source": r.question_source.key}
