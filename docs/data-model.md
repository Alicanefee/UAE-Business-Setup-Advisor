# Data Model

> Canonical records that every answer is built from. Schema: [`storage/schema.sql`](../storage/schema.sql). Seed files: [`data/seed/`](../data/seed/).

## Tables

| Table | Key fields | Notes |
|---|---|---|
| `laws` | `biz_type`, `emirate`, `activity`, `title`, `body`, `effective_from`, `effective_to`, `superseded_by` | `emirate = NULL` applies to all emirates; `activity = NULL` or `'general'` applies to all activities |
| `documents` | `law_id`, `name`, `issuer`, `how_to_obtain`, `is_mandatory`, `notes` | Required and optional documents per license |
| `penalties` | `law_id`, `condition`, `amount_aed`, `note`, effective window | `amount_aed` is text to allow ranges and non-monetary outcomes ("Renewal blocked") |
| `alternatives` | `missing_doc`, `alternative_doc`, `conditions`, effective window | `missing_doc` matches a document `name` exactly |
| `institutions` | `name`, `emirate`, `biz_type`, `address`, `website`, `phone`, `email`, `notes` | `emirate = NULL` and `biz_type = NULL` mark federal authorities |
| `rules` | `version`, `body` | Loaded from `config/rules/*.yaml`; `id` is the file name |

## Identifier conventions

| Prefix | Meaning | Example |
|---|---|---|
| `L-MAIN-<EMIRATE>-nnn` | Mainland license | `L-MAIN-DXB-001` |
| `L-FZ-<EMIRATE>-nnn` | Free zone license | `L-FZ-AUH-001` |
| `L-MNC-nnn` | Multinational structure | `L-MNC-001` |
| `D-MAIN-nnn`, `D-FZ-nnn` | Document | `D-FZ-004` |
| `P-<SCOPE>-nnn` | Penalty (`MAIN`, `FZ`, `CT` Corporate Tax, `UBO`) | `P-UBO-001` |
| `A-nnn` | Alternative document | `A-003` |
| `I-<BODY>-nnn` | Institution | `I-DMCC-001` |

A claim's source key is `<type>:<id>`, e.g. `law:L-FZ-DXB-001` or `rule:classifier`.

## Content hashes

Each source type has a fixed list of canonical fields (`CANONICAL` in [`storage/sqlite.py`](../storage/sqlite.py)). The SHA-256 of those fields, joined in order, is stored in every claim and recomputed at verification. Fields outside the list (for example a document's `notes`) can be edited without invalidating claims.

## Versioning

Records are never edited in place when the underlying regulation changes:

1. Set `effective_to` on the old row.
2. Insert the new row with a new `id` and `effective_from`.
3. Point the old row's `superseded_by` at the new `id`.

Queries only return rows in force on the request date, and the verifier independently rejects any claim whose source is outside its effective window.

## Extending coverage

Adding a free zone or activity requires data only — no code changes:

1. `laws.json`: one row for the license.
2. `documents.json`: one row per required or optional document, with `law_id` pointing to the license.
3. `institutions.json`: the authority that issues it.
4. Optionally `penalties.json` and `alternatives.json`.
5. If the activity is new, add its keywords to `config/rules/classifier.yaml` and its label to `config/templates/responses.en.yaml`.

Then add a golden case to [`tests/golden/cases.yaml`](../tests/golden/cases.yaml).

## Known gaps in the seed data

The seed data is a development sample, not a complete register:

- `L-FZ-DXB-002` (Dubai free zone consulting), `L-MAIN-AUH-001`, `L-FZ-AUH-001` and `L-MNC-001` have no document records, so new-setup requests for them abstain.
- `L-MAIN-DXB-002` (Dubai mainland professional) has one optional document only.
- Several Dubai free zones share one generic software license record; zone-specific packages are not modeled.

## Accuracy

The seed records are sample data for demonstration and testing purposes only. They have not been verified against official sources; fees, penalties, document requirements and contact details may be incomplete, outdated or incorrect. All legal obligations arising from their use remain solely with the user — see [DISCLAIMER.md](../DISCLAIMER.md). Each record must carry a review date and a reference to its official source before any production use — see [roadmap.md](roadmap.md).
