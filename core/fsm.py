"""Explicit finite state machine for the orchestrator.

Every transition is checked against the ALLOWED matrix, so no agent or code
path can silently skip a step.
"""
from enum import Enum


class State(str, Enum):
    START = "start"
    CLASSIFY = "classify"
    NEED_LOCATION = "need_location"
    NEED_ACTIVITY = "need_activity"
    ROUTE_LAW = "route_law"
    BRANCH = "branch"
    NEW_DOCS = "new_docs"
    NEW_INSTITUTIONS = "new_institutions"
    RENEW_UPLOAD = "renew_upload"
    RENEW_COMPARE = "renew_compare"
    RENEW_PENALTY = "renew_penalty"
    RENEW_ALTERNATIVE = "renew_alternative"
    COMPOSE = "compose"
    ABSTAIN = "abstain"
    DONE = "done"


ALLOWED: dict[State, set[State]] = {
    State.START: {State.CLASSIFY},
    State.CLASSIFY: {State.NEED_LOCATION, State.NEED_ACTIVITY, State.ROUTE_LAW, State.ABSTAIN},
    State.NEED_LOCATION: {State.CLASSIFY},
    State.NEED_ACTIVITY: {State.CLASSIFY},
    State.ROUTE_LAW: {State.BRANCH, State.ABSTAIN},
    State.BRANCH: {State.NEW_DOCS, State.RENEW_UPLOAD},
    State.NEW_DOCS: {State.NEW_INSTITUTIONS, State.ABSTAIN},
    State.NEW_INSTITUTIONS: {State.COMPOSE},
    State.RENEW_UPLOAD: {State.RENEW_COMPARE},
    State.RENEW_COMPARE: {State.RENEW_PENALTY, State.ABSTAIN},
    State.RENEW_PENALTY: {State.RENEW_ALTERNATIVE},
    State.RENEW_ALTERNATIVE: {State.COMPOSE},
    State.COMPOSE: {State.DONE, State.ABSTAIN},
    State.ABSTAIN: {State.DONE},
    State.DONE: set(),
}


class IllegalTransition(ValueError):
    pass


def transition(current: State, target: State) -> State:
    if target not in ALLOWED[current]:
        raise IllegalTransition(f"Illegal transition: {current.value} → {target.value}")
    return target
