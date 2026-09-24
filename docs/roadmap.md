# Roadmap

> Updated as the project evolves.

## v0.1 — Deterministic core (current)

- [x] Source-bound protocol (`SourceRef`, `Claim`, `AgentResult`)
- [x] Three-stage verifier (schema · existence + hash · effective window)
- [x] Abstention policy + expert escalation queue (JSON Lines)
- [x] Explicit state machine with an `ALLOWED` transition matrix
- [x] YAML rule engine; rules stored and hashed as sources
- [x] 8 agents: classifier, location, law router, documents, institutions, renewal check, penalties, alternatives
- [x] Template composer with a source on every rendered line
- [x] SQLite repository seeded from JSON
- [x] REST + SSE API, web UI, CLI
- [x] Tests: protocol, verifier / hallucination harness, FSM, golden cases, orchestrator, API
- [x] Optional vocabulary-constrained LLM fallback for the classifier

## v0.2 — Data quality and documents

- [ ] Add `source_url` and `last_reviewed` to every seed record; show them in answers
- [ ] Fill the known seed gaps (Dubai free zone consulting, Abu Dhabi mainland, ADGM, regional HQ documents)
- [ ] Zone-specific free zone packages (DMCC, IFZA, Meydan, RAKEZ) instead of one generic record
- [ ] Document pipeline: PDF/image ingest, OCR, field extraction, document-type classification
- [ ] `POST /v1/upload`; renewal compares uploaded documents instead of a name list
- [ ] Persistent SQLite session store

## v0.3 — Law changes

- [ ] Law version history, `superseded_by` chains and text diffs
- [ ] Renewal flags law changes since the license was last issued
- [ ] Background law watcher (effective-window sweeps)
- [ ] Institution refresher restricted to allow-listed official domains, TTL cache
- [ ] Provenance-bound retrieval: vector search to find records, verbatim-substring check against the canonical record before use

## v0.4 — Production API

- [ ] API keys (hashed) + JWT, roles and scopes
- [ ] Rate limiting (Redis), request ids, structured logs, uniform error envelope
- [ ] Admin API for records, session traces and the escalation queue
- [ ] Signed webhooks with retry queue
- [ ] Idempotency keys
- [ ] Docker Compose (API, Redis, volume-backed database)

## v1.0 — Multilingual and integrations

- [ ] Arabic and Turkish templates; Arabic vocabulary aliases in the classifier
- [ ] External adapters (DET, DMCC, FTA, MOHRE) behind licensed integrations, cache fallback
- [ ] Expert review dashboard for escalations
- [ ] Evaluation suite: golden cases per emirate and structure, abstention-rate tracking

## Principles

- No production claims before they are earned.
- No record without a source; no answer without a record.
- Abstaining is a correct outcome, not a failure to hide.
