import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from api import main

    monkeypatch.setattr(main.orchestrator, "records_dir", tmp_path)
    return TestClient(main.app)


def test_health(client):
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["records"]["laws"] == 8


def test_chat_result(client):
    body = client.post("/v1/chat", json={
        "message": "I want to set up a software company in Dubai, my clients are overseas",
    }).json()
    assert body["status"] == "result"
    assert "law:L-FZ-DXB-001" in body["sources"]


def test_chat_question_then_answer(client):
    first = client.post("/v1/chat", json={"message": "Software company, overseas clients"}).json()
    assert first["status"] == "question"
    second = client.post("/v1/chat", json={"session_id": first["session_id"],
                                           "message": "Dubai"}).json()
    assert second["status"] == "result"


def test_chat_rejects_unknown_mode(client):
    assert client.post("/v1/chat", json={"message": "x", "mode": "other"}).status_code == 422


def test_stream_event_order(client):
    with client.stream("POST", "/v1/chat/stream",
                       json={"message": "Trading company in Dubai selling to local customers"}) as r:
        text = "".join(r.iter_text())
    events = [line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("event: ")]
    assert events[0] == "session"
    assert events[-2:] == ["result", "end"]
    assert "state" in events


def test_frontend_is_served(client):
    assert "UAE Business Setup Advisor" in client.get("/").text
