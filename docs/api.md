# API Specification

> The API is the contract between every consumer — web UI, mobile app, partner integrations and internal admin tooling — and the advisor engine. It is designed around three principles: **source-bound responses**, **explicit versioning** and **least-privilege access**.
>
> v0.1 implements the public chat and health endpoints ([`api/main.py`](../api/main.py)). Everything marked **(planned)** is specified here and tracked in [roadmap.md](roadmap.md).

---

## 1. Overview

```
                      ┌──────────────────────────────────────┐
                      │              Consumers               │
                      │  Web UI · Mobile · Partner · Admin   │
                      └──────────────────┬───────────────────┘
                                         │
                      ┌──────────────────▼───────────────────┐
                      │          API Gateway Layer           │
                      │  AuthN · AuthZ · Rate limit · Log    │
                      └──────────────────┬───────────────────┘
        ┌────────────────────────────────┼────────────────────────────────┐
┌───────▼────────┐              ┌────────▼────────┐              ┌────────▼────────┐
│  Public API    │              │  Admin API      │              │  Webhook bus    │
│  /v1/chat      │              │  /admin/v1/*    │              │  outbound       │
│  /v1/upload    │              │  laws · docs    │              │  events         │
│  /v1/session   │              │  penalties      │              │  HMAC-signed    │
│  /v1/health    │              │  institutions   │              │  retry queue    │
└───────┬────────┘              └────────┬────────┘              └────────┬────────┘
        └────────────────────────────────┼────────────────────────────────┘
                      ┌──────────────────▼───────────────────┐
                      │       Orchestrator + agents          │
                      └──────────────────┬───────────────────┘
                      ┌──────────────────▼───────────────────┐
                      │   External adapters (opt-in)         │
                      │   DET · DMCC · FTA · MOHRE           │
                      └──────────────────────────────────────┘
```

## 2. Public API — chat (implemented)

### `POST /v1/chat`

Blocking variant for server-to-server integrations. Returns only the terminal outcome.

Request:

```json
{
  "session_id": null,
  "message": "I want to set up a software company in Dubai; my clients are overseas.",
  "mode": "new",
  "documents": []
}
```

| Field | Type | Notes |
|---|---|---|
| `session_id` | string \| null | Omit to start a session; send it back to answer a follow-up question |
| `message` | string (≤ 4000) | Free text |
| `mode` | `"new"` \| `"renew"` | Renewal compares `documents` against license requirements |
| `documents` | string[] (≤ 50) | Renewal only: names of documents the user holds |

Response — one of three statuses:

```json
{
  "session_id": "7f2e…",
  "status": "result",
  "answer": {
    "scenario": "new",
    "title": "New Setup Plan",
    "summary": [
      {"label": "Structure", "value": "Free zone", "source": "rule:classifier"},
      {"label": "Governing license", "value": "Dubai Free Zone — Software & Technology License",
       "source": "law:L-FZ-DXB-001"}
    ],
    "sections": [
      {"heading": "Required Documents",
       "items": [{"text": "Passport Copy (mandatory) — issued by Applicant. …",
                  "source": "document:D-FZ-001"}]}
    ],
    "sources": ["rule:classifier", "rule:location", "law:L-FZ-DXB-001", "document:D-FZ-001"],
    "disclaimer": "Demonstration only — based on unverified sample records. …"
  },
  "question": null,
  "abstain": null,
  "sources": ["rule:classifier", "…"]
}
```

```json
{"session_id": "7f2e…", "status": "question",
 "question": {"key": "location", "text": "Which emirate do you want to set up in? …",
              "source": "rule:location"}}
```

```json
{"session_id": "7f2e…", "status": "abstain",
 "abstain": {"text": "This case falls outside our verified records, so we will not guess. …",
             "reason": "no_law_in_force:mainland/Dubai/software_development"}}
```

### `POST /v1/chat/stream`

Same request body. Server-sent events — the primary UX channel:

```
event: session
data: {"session_id": "7f2e…"}

event: state
data: {"type": "state", "state": "classify"}

event: state
data: {"type": "state", "state": "route_law"}

…

event: result          (or: question | abstain)
data: {"type": "result", "answer": {…}, "sources": [...]}

event: end
data: {}
```

| Event | Meaning |
|---|---|
| `session` | Session id for follow-up requests |
| `state` | One per state-machine step |
| `question` | More information needed; send the answer with the same `session_id` |
| `result` | Composed answer; every line carries its source |
| `abstain` | No verified record covers the case; escalated to the expert queue |
| `error` | Internal error (no internals are exposed) |
| `end` | Stream complete |

### `GET /v1/health`

```json
{"status": "ok",
 "records": {"laws": 8, "documents": 15, "penalties": 10, "alternatives": 7,
             "institutions": 12, "rules": 4},
 "llm_fallback": false}
```

Interactive OpenAPI documentation is served at `/docs`.

## 3. Versioning

- The URL carries the major version: `/v1/...`. A breaking change → `/v2/...`.
- Non-breaking additions stay in the same version and are recorded in the changelog.
- Deprecation (planned): responses carry `Sunset: <RFC 1123 date>`, `Deprecation: true` and `Link: </v2/…>; rel="successor-version"` for a 6-month window.

## 4. Authentication & authorization (planned)

Two credential types, both resolved to a `Principal(subject, role, scopes, issued_at, expires_at)`:

- **API keys** — header `X-API-Key`, format `usa_live_<role>_<32 hex>`. Only SHA-256 hashes are stored; the raw key never touches the database. Loaded from a secret store, never committed.
- **JWT bearer tokens** — issued by `POST /v1/auth/login` for the web UI, HS256, 12-hour expiry, carrying `sub`, `role` and `scopes`.

| Role | Access |
|---|---|
| `public` | `POST /v1/chat*`, `POST /v1/upload`, own sessions only |
| `partner` | Public + higher rate limits + webhook subscriptions |
| `admin` | Everything, including `/admin/v1/*` |
| `service` | Internal only (agent-to-agent, watchers); not callable from outside the cluster |

Endpoints declare `require_role(...)` or `require_scope(...)` dependencies; failures return `401 unauthorized`, `403 forbidden` or `403 insufficient_scope`.

## 5. Rate limiting (planned)

Sliding-window limiter backed by Redis (in-memory for development), keyed by `scope:subject:window`. Exceeding a limit returns `429` with `Retry-After`.

| Role | chat | upload | read |
|---|---|---|---|
| `public` | 30 / min | 5 / hour | 60 / min |
| `partner` | 300 / min | 50 / hour | 600 / min |
| `admin` | 1,000 / min | 200 / hour | 2,000 / min |
| `service` | 10,000 / min | 1,000 / hour | 10,000 / min |

## 6. Observability (planned)

- `X-Request-ID` accepted or generated on every request and echoed in the response.
- Structured JSON access log per request: request id, method, path, status, duration, subject, role.
- Admin session trace: the full FSM path plus every claim and its source hash.

## 7. Error contract (planned)

Every error response has the same envelope — never a bare 500:

```json
{
  "error": {
    "code": "verification_failed",
    "message": "Source hash mismatch on L-MAIN-DXB-001",
    "request_id": "8f3c…",
    "agent": "law_router"
  }
}
```

| Code | HTTP | Meaning |
|---|---|---|
| `validation_error` | 422 | Invalid request body |
| `source_not_found` | 422 | A cited source does not exist |
| `verification_failed` | 422 | A source failed hash or effective-window checks |
| `abstained` | 409 | The system abstained (blocking admin/partner flows) |
| `unauthorized` / `forbidden` | 401 / 403 | Credentials missing or insufficient |
| `rate_limited` | 429 | Includes `limit`, `window_seconds`, `retry_after` |
| `upstream_error` | 502 | External adapter failure |

## 8. Public API — upload & sessions (planned)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/v1/upload` | Multipart (`session_id`, `file`). Allowed: `.pdf .png .jpg .jpeg .docx`, max 10 MB. Parsed by the document pipeline and attached to the session. `415` / `413` on violations. |
| `GET` | `/v1/session/{sid}` | Session facts, expected and uploaded documents, FSM state. Owner or admin only. |
| `DELETE` | `/v1/session/{sid}` | Owner or admin only. |
| `POST` | `/v1/escalate` | Open an expert case explicitly. |
| `GET` | `/v1/ready` | Readiness probe; fails if the database is unreachable. |

## 9. Admin API (planned)

Maintains the canonical records. Every write re-indexes the affected record and is itself logged.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/v1/laws` | List (filters: `biz_type`, `emirate`, `active_only`, `limit`) |
| `POST` | `/admin/v1/laws` | Create (`409 already_exists` on duplicate id) |
| `PUT` | `/admin/v1/laws/{id}` | Update |
| `POST` | `/admin/v1/laws/{id}/supersede` | Close the old version and link its successor |
| `GET` | `/admin/v1/laws/{id}/versions` | Version history |
| `POST` | `/admin/v1/laws/reindex` | Rebuild search indexes |
| `GET/POST/PUT/DELETE` | `/admin/v1/{documents,penalties,alternatives,institutions}/*` | CRUD |
| `GET` | `/admin/v1/sessions` | List sessions |
| `GET` | `/admin/v1/sessions/{sid}/trace` | Full FSM trace with every claim and source hash |
| `GET` | `/admin/v1/sessions/escalations` | Expert review queue |
| `POST/GET/DELETE` | `/admin/v1/webhooks` | Webhook subscriptions |

## 10. Webhooks (planned)

Signed outbound events for partners, delivered from an async queue.

| Event | When |
|---|---|
| `session.created` | A new session starts |
| `session.completed` | A result was composed |
| `session.abstained` | The system abstained |
| `document.uploaded` | A document was attached to a session |
| `law.superseded` | A law record was superseded |
| `escalation.opened` / `escalation.closed` | Expert queue changes |

Delivery headers: `X-Advisor-Event`, `X-Advisor-Signature`, `X-Advisor-Attempt`.

**Signature**: `t=<unix ts>,v1=<hex HMAC-SHA256(secret, "<ts>." + raw body)>`. Receivers must reject timestamps older than 5 minutes and compare signatures in constant time:

```python
import hashlib, hmac, time

def verify(secret: str, body: bytes, header: str, tolerance_s: int = 300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    ts = int(parts["t"])
    if abs(time.time() - ts) > tolerance_s:
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts["v1"])
```

**Retries**: up to 6 attempts with exponential backoff (2ⁿ seconds, capped at 1 hour); any 2xx response acknowledges delivery. Subscription secrets are shown once at creation.

## 11. External adapters (planned)

UAE authorities expose portals rather than public APIs. Adapters isolate that reality so the core never depends on a live government endpoint:

| Adapter | Path | Data |
|---|---|---|
| DET | `/internal/v1/external/det/license-status/{no}` | Dubai mainland license status |
| DMCC | `/internal/v1/external/dmcc/company/{no}` | Company registry |
| FTA | `/internal/v1/external/fta/tax-status/{trn}` | Corporate Tax / VAT status |
| MOHRE | `/internal/v1/external/mohre/wps/{no}` | WPS compliance |

Each adapter is `admin`/`service` only, calls the live service when a licensed integration is configured, otherwise serves from a local cache, and always attributes the response: `{"source": "det_live" | "local_cache", "data": {…}}`.

## 12. Full endpoint table

| Method | Path | Auth | Rate | Status |
|---|---|---|---|---|
| POST | `/v1/chat` | public+ | 30/min | ✅ implemented (no auth yet) |
| POST | `/v1/chat/stream` | public+ | 30/min | ✅ implemented (no auth yet) |
| GET | `/v1/health` | — | 120/min | ✅ implemented |
| POST | `/v1/auth/login` | — | 10/min | planned |
| GET | `/v1/auth/me` | any | 60/min | planned |
| POST | `/v1/upload` | public+ | 5/h | planned |
| GET / DELETE | `/v1/session/{sid}` | owner/admin | 60/min · 10/min | planned |
| GET | `/v1/ready` | — | 120/min | planned |
| POST | `/v1/escalate` | public+ | 5/h | planned |
| * | `/admin/v1/*` | admin | 30–200/min | planned |
| GET | `/internal/v1/external/*` | admin/service | 60/min | planned |

## 13. Configuration

See [`.env.example`](../.env.example). Planned additions: `JWT_SECRET`, `JWT_ALG`, `API_KEYS_FILE`, `REDIS_URL`, per-adapter `*_API_BASE` / `*_API_KEY`, `WEBHOOK_MAX_ATTEMPTS`, `WEBHOOK_TIMEOUT_S`.

## 14. Design principles

| Principle | How it shows up |
|---|---|
| **Source-bound responses** | Every result line carries a source key; `sources` lists exactly what was rendered |
| **Explicit errors** | Uniform envelope with `code`, `message`, `request_id` |
| **Idempotency** | `POST /v1/chat` will accept an `Idempotency-Key` header; repeats return the cached response for 24 h |
| **Versioning** | URL-prefixed major version, `Sunset` header on deprecation |
| **Least privilege** | Roles + scopes; `service` is not reachable from outside the cluster |
| **Observability** | Request ids, structured logs, admin session trace |
| **Streaming first** | SSE for the UI; blocking REST for server-to-server |
| **Webhook reliability** | HMAC signatures, timestamp tolerance, exponential backoff |
| **External isolation** | Adapters are swappable; the core never depends on a live government endpoint |
| **Abstention is an outcome** | A distinct `abstain` status/event, never a silent failure |
