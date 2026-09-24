"""In-memory session store.

A session accumulates the user's messages across turns so follow-up answers
("Dubai") are classified together with the original request.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    text: str = ""
    is_renewal: bool = False
    held_documents: list[str] = field(default_factory=list)
    completed: bool = False
    facts: dict = field(default_factory=dict)  # verified slot values, e.g. {"biz.type": "freezone"}


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> Session:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(id=session_id)
            return self._sessions[session_id]

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)
