from pathlib import Path

import pytest
import yaml

from tests.conftest import final_event

CASES = yaml.safe_load((Path(__file__).parent / "golden" / "cases.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_case(orchestrator, case):
    event, _ = final_event(orchestrator, case["input"], case.get("mode", "new"),
                           case.get("documents"))
    expect = case["expect"]
    assert event["type"] == expect["type"], event

    if event["type"] == "question":
        assert event["key"] == expect["key"]
    elif event["type"] == "abstain":
        assert event["reason"].startswith(expect["reason_prefix"])
    else:
        answer = event["answer"]
        summary = {row["label"]: row["value"] for row in answer["summary"]}
        slot_labels = {"biz.type": "Structure", "location.emirate": "Emirate"}
        for slot, label in slot_labels.items():
            if slot in expect:
                assert summary[label] == expect[slot]
        for key in expect.get("sources_include", []):
            assert key in event["sources"]
        if "missing" in expect:
            section = next(s for s in answer["sections"] if s["heading"] == "Missing Documents")
            names = [i["text"].split(" — ")[0] for i in section["items"]]
            assert names == expect["missing"]
