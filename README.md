# UAE Business Setup Advisor

> **Evidence-backed advisor for setting up and renewing a business in the UAE.**
> Mainland · Free zones · Multinationals — every claim is bound to a source record, and when there is no source, the system abstains instead of guessing.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: v0.1.0](https://img.shields.io/badge/status-v0.1.0-orange.svg)](docs/roadmap.md)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **For demonstration and testing purposes only.** All records in this repository are sample data and have not been verified against official sources. The output is not legal, tax or regulatory advice. **All legal obligations arising from use of this software remain solely with the user.** Read the full [Legal Disclaimer and Terms of Use](DISCLAIMER.md) before use.

---

## What it does

Founders, SMEs and multinationals ask the same questions when entering the UAE: *Mainland or free zone? Which license? Which documents, from which authority? What happens if a renewal is late?* The answers are scattered across emirate-level authorities, dozens of free zones and federal bodies — and a confident but wrong answer from a chatbot can cost months.

This advisor answers those questions **only from curated records**:

- **New setup** — structure (mainland / free zone / multinational), governing license, required documents, where to apply
- **Renewal** — which required documents are missing, applicable penalties, accepted alternative documents
- **Clarifying questions** — when the request is incomplete (emirate, activity, target market), it asks instead of assuming
- **Abstention** — when no verified record covers the case, it says so and logs the case to an escalation queue (intended for human expert review in a production deployment)

## How it prevents hallucination

| Principle | How it works |
|---|---|
| **Every claim has a source** | Agents return `Claim(slot, value, source)` objects. A claim cannot be constructed without a `SourceRef` — the canonical database row plus a SHA-256 hash of its content. |
| **Three-stage verification** | Before any claim is used: schema check → source exists and hash matches → source is in force today. A fabricated, tampered or expired source is rejected. |
| **The LLM never writes answers** | Classification is deterministic (keyword vocabularies + YAML rules). An optional LLM fallback may only choose values from fixed vocabularies. Every sentence the user reads comes from a template. |
| **Abstain, don't guess** | Missing mandatory facts, low confidence, or a failed verification → the request is escalated to `records/escalations.jsonl`, never answered. |
| **Explicit state machine** | Every step transition is checked against an `ALLOWED` matrix; no code path can silently skip classification, routing or verification. |
| **Rules are sources too** | The classifier and location rules live in `config/rules/*.yaml`, are loaded into the database and hashed — so rule changes are visible in every answer that cites them. |

## Architecture

```
┌──────────────────┐   ┌──────────────┐
│  Web UI (SSE)    │   │  CLI         │
└────────┬─────────┘   └──────┬───────┘
         └──────────┬─────────┘
┌───────────────────▼──────────────────────────────────────────────┐
│  API (FastAPI)   POST /v1/chat · POST /v1/chat/stream · /v1/health │
└───────────────────┬──────────────────────────────────────────────┘
┌───────────────────▼──────────────────────────────────────────────┐
│  Orchestrator — explicit FSM                                      │
│                                                                   │
│  CLASSIFY → ROUTE_LAW → BRANCH ─┬─ NEW_DOCS → NEW_INSTITUTIONS ─┐ │
│      │                          └─ RENEW_UPLOAD → RENEW_COMPARE │ │
│      │                             → RENEW_PENALTY → RENEW_ALT ─┤ │
│      ▼                                                          ▼ │
│  NEED_ACTIVITY / NEED_LOCATION (ask user)      COMPOSE ── ABSTAIN │
│                                                                   │
│  Every agent result ──▶ 3-stage Verifier ──▶ Abstention policy    │
│                                         ──▶ Composer (templates)  │
└───────────────────┬──────────────────────────────────────────────┘
┌───────────────────▼──────────────┐   ┌───────────────────────────┐
│  SQLite (canonical records)      │   │  records/escalations.jsonl │
│  laws · documents · penalties ·  │   │  (escalation queue)        │
│  alternatives · institutions ·   │   └───────────────────────────┘
│  rules                           │
└──────────────────────────────────┘
```

📖 Full design: [`docs/architecture.md`](docs/architecture.md) · API specification: [`docs/api.md`](docs/api.md) · Data model: [`docs/data-model.md`](docs/data-model.md) · Roadmap: [`docs/roadmap.md`](docs/roadmap.md)

## Quick start

```bash
git clone https://github.com/Alicanefee/UAE-Business-Setup-Advisor.git
cd UAE-Business-Setup-Advisor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the tests
pytest

# Try it from the command line
python cli.py "I want to set up a software company in Dubai; my clients are overseas"

# Or start the web UI + API
uvicorn api.main:app --reload     # open http://localhost:8000 — API docs at /docs
```

No API key is needed: the system runs fully deterministic by default. Set `OPENAI_API_KEY` in `.env` (and `pip install openai`) to enable the optional LLM fallback for unusual phrasing.

## Example

```
$ python cli.py "Trading company in Dubai selling to local customers"
[flow] start → classify → route_law → branch → new_docs → new_institutions → compose

New Setup Plan
==============
Structure          Mainland  [rule:classifier]
Emirate            Dubai  [rule:location]
Activity           Commercial trading  [rule:classifier]
Governing license  Dubai Mainland Commercial License — DET (DED)  [law:L-MAIN-DXB-001]

Required Documents
  - Passport Copy (All Shareholders & Managers) (mandatory) — issued by Applicant. ...  [document:D-MAIN-001]
  - Memorandum of Association (MOA) (mandatory) — issued by Notary Public. ...  [document:D-MAIN-003]
  - Ejari Tenancy Contract (mandatory) — issued by Dubai Land Department. ...  [document:D-MAIN-004]
  ...

Where to Apply
  - Dubai Economy and Tourism (DET / DED), Business Bay, Dubai, UAE — https://www.dubaided.gov.ae  [institution:I-DET-001]
  ...
```

When no record covers the request, it abstains:

```
$ python cli.py "Software company in Dubai selling to local customers"
[flow] start → classify → route_law → abstain

! This case falls outside our verified records, so we will not guess. It has been logged to the escalation queue (demonstration only — no human review).
  (reason: no_law_in_force:mainland/Dubai/software_development)
```

Renewal mode compares the documents you hold against the license requirements:

```
$ python cli.py "Renew my Dubai free zone software license" --renew \
    --documents "Passport copy; Passport-size photograph; Application form"

Missing Documents
  - Proof of Address (Utility Bill) — issued by Applicant. ...  [document:D-FZ-002]
Possible Penalties
  - Operating with an expired license: AED 5,000. ...  [penalty:P-FZ-001]
  - IFZA — financial statements not submitted: Renewal blocked. ...  [penalty:P-FZ-005]
```

## Current state

- **Status**: v0.1.0 — deterministic core, end-to-end flows for new setup and renewal
- **Implemented**: source-bound protocol, 3-stage verifier, abstention policy, explicit FSM, YAML rule engine, 8 agents, template composer, SQLite repository with seed data, expert escalation queue, REST + SSE API, web UI, CLI, 38 tests (including a hallucination harness)
- **Not yet implemented**: document upload with OCR, vector retrieval, law version diffing and background watchers, authentication / rate limiting / admin API / webhooks, Arabic and Turkish templates — see [`docs/roadmap.md`](docs/roadmap.md)
- **Coverage**: the seed data covers a limited set of Dubai, Abu Dhabi and federal records. Requests outside it abstain by design.

## Repository layout

```
UAE-Business-Setup-Advisor/
├── DISCLAIMER.md                ← Demonstration-only terms and user responsibility
├── api/main.py                  ← FastAPI app: /v1/chat, /v1/chat/stream, /v1/health, static UI
├── cli.py                       ← Command-line demo
├── core/
│   ├── protocol.py              ← SourceRef, Claim, AgentResult
│   ├── verifier.py              ← 3-stage verification
│   ├── abstention.py            ← Abstention policy
│   ├── fsm.py                   ← States + ALLOWED transition matrix
│   └── settings.py
├── agents/
│   ├── classifier.py            ← Structure + activity (rules first, optional LLM fallback)
│   ├── location.py              ← Emirate
│   ├── law_router.py            ← Governing license record
│   ├── document.py              ← Required documents
│   ├── institution.py           ← Where to apply
│   └── renewal.py               ← Document check, penalties, alternatives
├── services/
│   ├── orchestrator.py          ← FSM driver, verification, composition, escalation
│   ├── composer.py              ← Template rendering with per-line sources
│   ├── escalation.py            ← Escalation queue (JSON Lines)
│   └── llm.py                   ← Optional vocabulary-constrained LLM extractor
├── storage/
│   ├── schema.sql
│   ├── sqlite.py                ← Repository + canonical hash fields
│   └── session.py
├── config/
│   ├── rules/                   ← classifier, location, renewal, abstention (YAML, hashed)
│   └── templates/responses.en.yaml
├── data/seed/                   ← laws, documents, penalties, alternatives, institutions
├── frontend/                    ← index.html, app.js (SSE client), style.css
├── tests/                       ← protocol, verifier, FSM, golden cases, orchestrator, API
└── docs/                        ← architecture, api, data-model, roadmap
```

## ⚠️ Disclaimer

- **This project is for demonstration and testing purposes only.** It must not be used for real business setup, license renewal or compliance decisions.
- The records in `data/seed/` are **sample data** compiled for development and testing. They have not been verified against official sources and may be incomplete, outdated or incorrect.
- The output is **not legal, tax, financial or regulatory advice**.
- **The user is solely responsible** for verifying all requirements with the issuing authorities and for **all legal, regulatory, tax and financial obligations** arising from use of this software or decisions based on its output.
- The author accepts no liability for any loss, penalty or other consequence arising from its use.
- This is independent R&D and is not affiliated with or endorsed by any UAE authority or free zone.

Full terms: [DISCLAIMER.md](DISCLAIMER.md).

## Author

**Ali Can Efe** — Medical device industry expert and advisor with 13 years of experience across different departments: product management, regulatory compliance and AI-enabled imaging, with global expertise including the Middle East, Turkey & Africa (META).

## License

MIT — see [LICENSE](LICENSE).
