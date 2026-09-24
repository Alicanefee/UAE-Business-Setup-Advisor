"""Expert escalation queue. Cases the system abstains on are appended to
records/escalations.jsonl for human review."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.protocol import AgentResult


def escalate(records_dir: Path, session, reason: str, results: list[AgentResult]) -> dict:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session.id,
        "reason": reason,
        "request": session.text,
        "is_renewal": session.is_renewal,
        "facts": session.facts,
        "agents": [{"agent": r.agent, "status": r.status, "reason": r.reason} for r in results],
    }
    records_dir.mkdir(parents=True, exist_ok=True)
    with (records_dir / "escalations.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
