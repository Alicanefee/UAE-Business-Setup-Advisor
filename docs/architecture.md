# Architecture

> How the advisor turns a free-text request into a fully sourced answer — or a deliberate abstention.
> Components marked **(planned)** are specified here and tracked in [roadmap.md](roadmap.md).

---

## 1. Design goals

1. **No unsourced statement reaches the user.** Every fact is bound to one canonical record.
2. **Language models classify; they never compose.** User-facing text comes from templates.
3. **Uncertainty is a first-class outcome.** Missing facts lead to a question; missing records lead to an abstention and an expert escalation.
4. **Every step is explicit and auditable.** A finite state machine governs the flow; rule sets are versioned and hashed like data.

## 2. Request lifecycle

```
user text
   │
   ▼
CLASSIFY ──────────► NEED_ACTIVITY / NEED_LOCATION ──► question to user (turn ends)
   │                                                     next message restarts at CLASSIFY
   ▼
ROUTE_LAW ─────────► ABSTAIN (no law in force for structure/emirate/activity)
   │
   ▼
BRANCH
   ├─ new setup ──► NEW_DOCS ──► NEW_INSTITUTIONS ──────────────┐
   └─ renewal ────► RENEW_UPLOAD ──► RENEW_COMPARE ──►          │
                    RENEW_PENALTY ──► RENEW_ALTERNATIVE ────────┤
                                                                ▼
                                                    COMPOSE ──► result
                                                       │
                                                       └──────► ABSTAIN ──► escalation
```

The full transition matrix lives in [`core/fsm.py`](../core/fsm.py). `transition()` raises `IllegalTransition` for any edge not in `ALLOWED`, so no step can be skipped silently.

## 3. Source-bound protocol

[`core/protocol.py`](../core/protocol.py)

| Type | Purpose |
|---|---|
| `SourceRef` | `type` + `id` of a canonical row, a SHA-256 `hash` of its canonical fields, `retrieved_at`, effective window |
| `Claim` | `slot` (template slot), `value`, `source: SourceRef`, `confidence` — a claim cannot exist without a source |
| `AgentResult` | `ok` (non-empty claims), `need_info` (a question key **with** a source), or `abstain` (a reason) |

Agents cannot return free-form data. The composer only knows how to render claims, and only for slots that exist in the template — anything else is dropped.

The canonical fields covered by each hash are defined per source type in [`storage/sqlite.py`](../storage/sqlite.py) (`CANONICAL`). Changing any of those fields in the database invalidates every claim that cites the row.

## 4. Three-stage verifier

[`core/verifier.py`](../core/verifier.py) — every `ok` result passes through it before its claims are used.

| Stage | Check | Rejects |
|---|---|---|
| 1. Schema | slot and value present | empty or malformed claims |
| 2. Existence + hash | row exists; recomputed hash equals the claim's hash | invented sources, forged hashes, rows changed after retrieval |
| 3. Effective window | `effective_from ≤ today ≤ effective_to` (from the database row, not the claim) | expired or not-yet-effective records |

A failure never surfaces as an answer: the orchestrator converts it into an abstention with reason `verification_failed: …`. The hallucination harness in [`tests/test_verifier.py`](../tests/test_verifier.py) forges a document claim mid-flow and asserts that no result is produced.

## 5. Abstention policy

[`core/abstention.py`](../core/abstention.py) + [`config/rules/abstention.yaml`](../config/rules/abstention.yaml)

The composer is only reached when:
- no agent abstained,
- the lowest claim confidence is at least `min_confidence` (0.65),
- every mandatory slot — `biz.type`, `location.emirate`, `biz.activity`, `laws.primary` — is backed by a verified claim.

Otherwise the request is written to `records/escalations.jsonl` with the session facts and each agent's status, and the user receives the abstention template.

Optional sections (institutions, penalties, alternatives) are included when records exist and omitted when they do not; they never block an answer. Required sections (documents for a new setup, the document check for a renewal) abstain when no records exist.

## 6. Rule engine

Rules are YAML files in [`config/rules/`](../config/rules/). At startup each file is stored in the `rules` table and hashed; agents load their configuration **from the database row**, so the rules they apply are exactly the rules they cite (`rule:classifier`, `rule:location`, …).

**Classifier** ([`agents/classifier.py`](../agents/classifier.py)):
1. Extract signals with whole-word keyword matching: explicit structure ("free zone", "mainland"), activity, target market.
2. *(optional)* If a signal is missing and `OPENAI_API_KEY` is set, ask an LLM to choose from the same fixed vocabularies. Values outside the vocabularies are discarded; LLM-derived signals carry a lower confidence (0.7).
3. Decide the structure: the user's explicit choice wins; otherwise the first matching rule (`R-MNC-HQ`, `R-LOCAL-MARKET`, `R-FZ-EXPORT`) applies.
4. If a signal is still missing, return a targeted question (`describe_business`, `activity`, `target_market`, `structure`).

Conditions are structured data (`when: {activity: [...], target_market: [...]}`), not evaluated expressions — there is no `eval` anywhere in the rule path.

## 7. Agents

| Agent | Input | Output slots | Source types |
|---|---|---|---|
| `classifier` | request text | `biz.type`, `biz.activity` | rule |
| `location` | request text | `location.emirate` | rule |
| `law_router` | structure, emirate, activity, date | `laws.primary` | law |
| `document` | law id | `documents` | document |
| `institution` | emirate, structure | `institutions` | institution |
| `renewal_check` | law id, documents held | `renewal.missing`, `renewal.matched` | document |
| `penalty` | law id, date | `penalties` | penalty |
| `alternative` | missing document names, date | `alternatives` | alternative |

The law router returns the most specific law in force (emirate-specific before federal, activity-specific before general).

## 8. Composer

[`services/composer.py`](../services/composer.py) + [`config/templates/responses.en.yaml`](../config/templates/responses.en.yaml)

- Summary rows and section items are filled from verified claims only, using `str.format_map` over the claim's value (no template engine, no code execution).
- Each rendered line carries its source key (`law:L-FZ-DXB-001`, `document:D-FZ-002`, …), and `sources` lists exactly the sources that were rendered.
- Questions, the abstention message and the disclaimer also come from the template file.

## 9. Storage

- **Canonical records** — SQLite, seeded from [`data/seed/`](../data/seed/) and [`config/rules/`](../config/rules/). In-memory by default (`SQLITE_PATH=:memory:`), so every start is reproducible. See [data-model.md](data-model.md).
- **Sessions** — in memory; a session accumulates the user's messages until a request completes, so a follow-up such as "Dubai" is classified together with the original request.
- **Escalations** — append-only JSON Lines in `records/escalations.jsonl`.

## 10. Planned components

| Component | Purpose |
|---|---|
| **Document pipeline** (planned) | `docs_pipeline/`: PDF/image ingest (pdfplumber, Tesseract OCR), field extraction, document-type classification, comparison against expected documents. Replaces the "documents held" name list in renewal mode. |
| **Provenance-bound retrieval** (planned) | `rag/`: vector search is used only to *find* candidate records. A retrieved chunk is accepted only if it is a verbatim substring of its canonical record, and it then travels with that record's `SourceRef`. Retrieval is never evidence on its own. |
| **Law versioning** (planned) | `laws/`: version history per law, `superseded_by` chains, text diffs between versions, and a renewal check that flags law changes since the last license issue. |
| **Background watchers** (planned) | A law watcher that sweeps effective windows, and an institution refresher that only contacts allow-listed official domains and writes to a TTL cache. User requests read from cache only — never from the network. |
| **Persistent sessions + trace** (planned) | SQLite session store and a per-request trace (FSM path, every claim and its source hash) for the admin API. |
| **Multilingual templates** (planned) | `responses.ar.yaml` and `responses.tr.yaml`; the classifier vocabularies gain Arabic aliases. |
| **Records export** (planned) | Asynchronous client-record export to Excel via a background queue, so user requests never block on file I/O. |
| **Production API** (planned) | Authentication, rate limiting, admin CRUD, webhooks and external adapters as specified in [api.md](api.md). |

## 11. Why this design limits hallucination

| Failure mode | Defense |
|---|---|
| Model invents a fact | Facts are claims; claims need a source row; stage 2 rejects unknown rows |
| Model cites a real record but alters it | The hash of the altered content does not match the row |
| Record changes after it was read | Recomputed hash differs at verification time |
| Outdated law or penalty | Stage 3 checks the effective window from the database |
| Unknown combination (e.g. mainland software in Dubai with no record) | Law router finds nothing → abstain → escalation queue |
| Missing information | Targeted question instead of an assumption |
| Step skipped by a bug | `ALLOWED` matrix raises `IllegalTransition` |
| Prompt injection into generated text | The LLM never generates user-facing text |
