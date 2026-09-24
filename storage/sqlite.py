"""SQLite repository for canonical source records.

The database is seeded from data/seed/*.json and config/rules/*.yaml. Agents
read from here; nothing else is a valid source of facts.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date
from pathlib import Path

import yaml

from core.protocol import SourceType
from core.settings import RULES_DIR, SEED_DIR, SQLITE_PATH

SCHEMA = Path(__file__).with_name("schema.sql")

# Seed order matters: laws must exist before documents and penalties reference them.
TABLES: dict[SourceType, str] = {
    SourceType.LAW: "laws",
    SourceType.DOCUMENT: "documents",
    SourceType.PENALTY: "penalties",
    SourceType.ALTERNATIVE: "alternatives",
    SourceType.INSTITUTION: "institutions",
    SourceType.RULE: "rules",
}

# Fields covered by a source's content hash. Changing any of them invalidates
# every claim that cites the row.
CANONICAL: dict[SourceType, list[str]] = {
    SourceType.LAW: ["id", "biz_type", "emirate", "activity", "title", "body",
                     "effective_from", "effective_to", "superseded_by"],
    SourceType.DOCUMENT: ["id", "law_id", "name", "issuer", "how_to_obtain", "is_mandatory"],
    SourceType.PENALTY: ["id", "law_id", "condition", "amount_aed", "note",
                         "effective_from", "effective_to"],
    SourceType.ALTERNATIVE: ["id", "missing_doc", "alternative_doc", "conditions",
                             "effective_from", "effective_to"],
    SourceType.INSTITUTION: ["id", "name", "emirate", "biz_type", "address", "website"],
    SourceType.RULE: ["id", "version", "body"],
}


class Repository:
    def __init__(self, path: str = SQLITE_PATH, seed_dir: Path = SEED_DIR,
                 rules_dir: Path = RULES_DIR):
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        self._seed(seed_dir)
        self._load_rules(rules_dir)

    # ── bootstrap ────────────────────────────────────────────────────────

    def _columns(self, table: str) -> list[str]:
        return [r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")]

    def _seed(self, seed_dir: Path) -> None:
        for type_, table in TABLES.items():
            if type_ is SourceType.RULE:
                continue
            f = seed_dir / f"{table}.json"
            if not f.exists():
                continue
            if self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0:
                continue
            rows = json.loads(f.read_text(encoding="utf-8"))
            cols = self._columns(table)
            q = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
            self.conn.executemany(q, [tuple(r.get(c) for c in cols) for r in rows])
        self.conn.commit()

    def _load_rules(self, rules_dir: Path) -> None:
        for f in sorted(rules_dir.glob("*.yaml")):
            body = f.read_text(encoding="utf-8")
            version = int((yaml.safe_load(body) or {}).get("version", 1))
            self.conn.execute(
                "INSERT OR REPLACE INTO rules (id, version, body) VALUES (?, ?, ?)",
                (f.stem, version, body),
            )
        self.conn.commit()

    # ── generic access ───────────────────────────────────────────────────

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute(sql, params)]

    def fetch_source(self, type_: SourceType | str, id_: str) -> dict | None:
        table = TABLES[SourceType(type_)]
        rows = self._all(f"SELECT * FROM {table} WHERE id = ?", (id_,))
        return rows[0] if rows else None

    def canonical_fields(self, type_: SourceType | str) -> list[str]:
        return CANONICAL[SourceType(type_)]

    def count(self, table: str) -> int:
        if table not in TABLES.values():
            raise ValueError(f"Unknown table: {table}")
        return self._all(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]

    # ── domain queries ───────────────────────────────────────────────────

    def find_laws(self, biz_type: str, emirate: str | None, activity: str | None,
                  on: date) -> list[dict]:
        """Laws in force on `on`, most specific first."""
        day = on.isoformat()
        return self._all(
            """
            SELECT * FROM laws
            WHERE biz_type = ?
              AND (emirate IS NULL OR emirate = ?)
              AND (activity IS NULL OR activity = 'general' OR activity = ?)
              AND effective_from <= ?
              AND (effective_to IS NULL OR effective_to >= ?)
            ORDER BY (emirate IS NULL), (activity IS NULL OR activity = 'general'), id
            """,
            (biz_type, emirate, activity, day, day),
        )

    def documents_for_law(self, law_id: str) -> list[dict]:
        return self._all(
            "SELECT * FROM documents WHERE law_id = ? ORDER BY is_mandatory DESC, id",
            (law_id,),
        )

    def penalties_for_law(self, law_id: str, on: date) -> list[dict]:
        day = on.isoformat()
        return self._all(
            """
            SELECT * FROM penalties
            WHERE law_id = ? AND effective_from <= ?
              AND (effective_to IS NULL OR effective_to >= ?)
            ORDER BY id
            """,
            (law_id, day, day),
        )

    def alternatives_for(self, missing_docs: list[str], on: date) -> list[dict]:
        if not missing_docs:
            return []
        day = on.isoformat()
        ph = ",".join("?" * len(missing_docs))
        return self._all(
            f"""
            SELECT * FROM alternatives
            WHERE missing_doc IN ({ph}) AND effective_from <= ?
              AND (effective_to IS NULL OR effective_to >= ?)
            ORDER BY id
            """,
            (*missing_docs, day, day),
        )

    def institutions_for(self, emirate: str, biz_type: str) -> list[dict]:
        """Institutions for the emirate and structure, plus federal authorities."""
        return self._all(
            """
            SELECT * FROM institutions
            WHERE (emirate IS NULL OR emirate = ?)
              AND (biz_type IS NULL OR biz_type = ?)
            ORDER BY (emirate IS NULL), id
            """,
            (emirate, biz_type),
        )
