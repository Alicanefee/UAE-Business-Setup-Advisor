import json

from tests.conftest import final_event


def test_every_rendered_line_has_a_source(orchestrator):
    event, _ = final_event(orchestrator, "Software company in Dubai, clients overseas")
    answer = event["answer"]
    lines = answer["summary"] + [i for s in answer["sections"] for i in s["items"]]
    assert lines and all(line["source"] for line in lines)
    assert set(answer["sources"]) == {line["source"] for line in lines}


def test_follow_up_answer_completes_the_request(orchestrator):
    first, _ = final_event(orchestrator, "Software company, overseas clients", session="s")
    assert first["type"] == "question" and first["key"] == "location"
    second, _ = final_event(orchestrator, "Dubai", session="s")
    assert second["type"] == "result"


def test_completed_session_starts_fresh(orchestrator):
    final_event(orchestrator, "Software company in Dubai, clients overseas", session="s")
    event, _ = final_event(orchestrator, "Abu Dhabi", session="s")
    assert event["type"] == "question"  # previous request text was cleared


def test_abstention_is_escalated(orchestrator, tmp_path):
    final_event(orchestrator, "Software company in Dubai selling to local customers")
    lines = (tmp_path / "escalations.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[-1])
    assert record["reason"].startswith("no_law_in_force")
    assert record["facts"]["biz.type"] == "mainland"
