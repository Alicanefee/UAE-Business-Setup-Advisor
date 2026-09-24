"""HTTP API (v1).

Implements the public chat and health endpoints. Authentication, rate
limiting, admin CRUD and webhooks are specified in docs/api.md and tracked in
docs/roadmap.md.
"""
from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.settings import FRONTEND_DIR, MODEL_NAME, OPENAI_API_KEY
from services.llm import build_llm
from services.orchestrator import Orchestrator
from storage.sqlite import Repository

repo = Repository()
orchestrator = Orchestrator(repo, llm=build_llm(OPENAI_API_KEY, MODEL_NAME))

app = FastAPI(
    title="UAE Business Setup Advisor API",
    version="0.1.0",
    description=(
        "Evidence-backed UAE business setup advisor. Every statement in a response "
        "is bound to a source record; when no source exists, the system abstains."
    ),
)


class ChatIn(BaseModel):
    session_id: str | None = None
    message: str = Field(default="", max_length=4000)
    mode: Literal["new", "renew"] = "new"
    documents: list[str] = Field(default_factory=list, max_length=50,
                                 description="Renewal only: names of documents currently held.")


class ChatOut(BaseModel):
    session_id: str
    status: Literal["result", "question", "abstain"]
    answer: dict | None = None
    question: dict | None = None
    abstain: dict | None = None
    sources: list[str] = []


@app.post("/v1/chat", response_model=ChatOut, tags=["chat"])
def chat(body: ChatIn) -> ChatOut:
    """Blocking variant: returns only the terminal event."""
    sid = body.session_id or str(uuid4())
    events = orchestrator.stream(sid, body.message, body.mode, body.documents)
    final = [e for e in events if e["type"] != "state"][-1]
    if final["type"] == "result":
        return ChatOut(session_id=sid, status="result", answer=final["answer"],
                       sources=final["sources"])
    if final["type"] == "question":
        return ChatOut(session_id=sid, status="question",
                       question={k: final[k] for k in ("key", "text", "source")})
    return ChatOut(session_id=sid, status="abstain",
                   abstain={"text": final["text"], "reason": final["reason"]})


@app.post("/v1/chat/stream", tags=["chat"])
def chat_stream(body: ChatIn) -> StreamingResponse:
    """Server-sent events: one `state` event per FSM step, then one terminal event."""
    sid = body.session_id or str(uuid4())

    def gen():
        yield _sse("session", {"session_id": sid})
        try:
            for ev in orchestrator.stream(sid, body.message, body.mode, body.documents):
                yield _sse(ev["type"], ev)
        except Exception:  # never leak internals into the stream
            yield _sse("error", {"code": "stream_error", "message": "Internal error"})
        yield _sse("end", {})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/v1/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "records": {t: repo.count(t) for t in
                    ("laws", "documents", "penalties", "alternatives", "institutions", "rules")},
        "llm_fallback": orchestrator.classifier.llm is not None,
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"


# Static frontend — mounted last so it does not shadow the API routes.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")
