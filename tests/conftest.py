from datetime import date

import pytest

from services.orchestrator import Orchestrator
from storage.sqlite import Repository

TODAY = date(2026, 9, 24)


@pytest.fixture
def repo():
    return Repository(":memory:")


@pytest.fixture
def orchestrator(repo, tmp_path):
    return Orchestrator(repo, records_dir=tmp_path, today=lambda: TODAY)


def final_event(orchestrator, message, mode="new", documents=None, session="s1"):
    events = list(orchestrator.stream(session, message, mode, documents))
    return events[-1], [e["state"] for e in events if e["type"] == "state"]
