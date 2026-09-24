import pytest

from core.fsm import ALLOWED, IllegalTransition, State, transition


def test_allowed_transition():
    assert transition(State.START, State.CLASSIFY) is State.CLASSIFY


@pytest.mark.parametrize("current,target", [
    (State.START, State.COMPOSE),          # cannot skip classification
    (State.CLASSIFY, State.NEW_DOCS),      # cannot skip law routing
    (State.NEW_DOCS, State.DONE),          # cannot finish without composing
    (State.DONE, State.CLASSIFY),          # terminal
])
def test_illegal_transition_raises(current, target):
    with pytest.raises(IllegalTransition):
        transition(current, target)


def test_every_state_reaches_done():
    reachable = {State.DONE}
    changed = True
    while changed:
        changed = False
        for state, targets in ALLOWED.items():
            if state not in reachable and targets & reachable:
                reachable.add(state)
                changed = True
    # NEED_* states hand control back to the user, then restart at CLASSIFY.
    assert set(State) - reachable == set()
