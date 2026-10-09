from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from config_settings import DB_PATH

FINDING_COLUMNS = [
    "id","is_demo","jurisdiction","geographic_level","authority","source_name","source_url",
    "original_title","english_title","original_language","publication_date","effective_date",
    "compliance_deadline","legislative_status","instrument_type","compliance_domain","category",
    "subcategory","affected_parties","key_obligations","key_changes","business_impact",
    "recommended_follow_up","confidence_score","evidence_excerpt","retrieved_at","finding_summary","ai_summary",
    "ai_analysis","user_notes"
]
SOURCE_COLUMNS = [
    "id","jurisdiction","authority","name","url","source_type","language","verification_status",
    "retrieval_method","active","last_success","last_failure","error_state","last_checked",
    "discovered_automatically","discovery_reason"
]


def connect(path: Path | str = DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _ensure_column(con, table: str, column: str, definition: str):
    existing = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db(path: Path | str = DB_PATH):
    with connect(path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY, is_demo INTEGER NOT NULL DEFAULT 0, jurisdiction TEXT NOT NULL,
                geographic_level TEXT NOT NULL, authority TEXT, source_name TEXT, source_url TEXT,
                original_title TEXT, english_title TEXT, original_language TEXT, publication_date TEXT,
                effective_date TEXT, compliance_deadline TEXT, legislative_status TEXT, instrument_type TEXT,
                compliance_domain TEXT, category TEXT, subcategory TEXT, affected_parties TEXT,
                key_obligations TEXT, key_changes TEXT, business_impact TEXT, recommended_follow_up TEXT,
                confidence_score REAL, evidence_excerpt TEXT, retrieved_at TEXT, finding_summary TEXT, ai_summary TEXT,
                ai_analysis TEXT, user_notes TEXT, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS finding_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id TEXT NOT NULL, field_name TEXT NOT NULL,
                previous_value TEXT, new_value TEXT, changed_at TEXT NOT NULL, change_type TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY, jurisdiction TEXT NOT NULL, authority TEXT, name TEXT NOT NULL, url TEXT NOT NULL,
                source_type TEXT, language TEXT, verification_status TEXT NOT NULL, retrieval_method TEXT,
                active INTEGER NOT NULL DEFAULT 1, last_success TEXT, last_failure TEXT, error_state TEXT,
                last_checked TEXT, discovered_automatically INTEGER NOT NULL DEFAULT 0, discovery_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS runtime_state (
                key TEXT PRIMARY KEY, value TEXT, updated_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(con, "sources", "discovered_automatically", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(con, "sources", "discovery_reason", "TEXT")
        _ensure_column(con, "findings", "finding_summary", "TEXT")


def _now():
    return datetime.now(timezone.utc).isoformat()


def upsert_finding(record: dict, path: Path | str = DB_PATH, change_type: str = "manual"):
    clean = {k: record.get(k) for k in FINDING_COLUMNS}
    clean["is_demo"] = int(bool(clean.get("is_demo")))
    with connect(path) as con:
        existing = con.execute("SELECT * FROM findings WHERE id=?", (clean["id"],)).fetchone()
        if existing:
            for field in FINDING_COLUMNS:
                old = existing[field]
                new = clean.get(field)
                if str(old if old is not None else "") != str(new if new is not None else ""):
                    con.execute(
                        "INSERT INTO finding_versions (finding_id,field_name,previous_value,new_value,changed_at,change_type) VALUES (?,?,?,?,?,?)",
                        (clean["id"], field, old, new, _now(), change_type),
                    )
        placeholders = ",".join(["?"] * (len(FINDING_COLUMNS) + 1))
        columns = ",".join(FINDING_COLUMNS + ["updated_at"])
        updates = ",".join([f"{c}=excluded.{c}" for c in FINDING_COLUMNS[1:]] + ["updated_at=excluded.updated_at"])
        con.execute(
            f"INSERT INTO findings ({columns}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
            [clean[c] for c in FINDING_COLUMNS] + [_now()],
        )


def purge_demo_findings(path: Path | str = DB_PATH):
    with connect(path) as con:
        con.execute("DELETE FROM finding_versions WHERE finding_id IN (SELECT id FROM findings WHERE is_demo=1)")
        con.execute("DELETE FROM findings WHERE is_demo=1")


def list_findings(path: Path | str = DB_PATH) -> pd.DataFrame:
    with connect(path) as con:
        return pd.read_sql_query("SELECT * FROM findings ORDER BY publication_date DESC, updated_at DESC", con)


def get_finding(finding_id: str, path: Path | str = DB_PATH) -> dict | None:
    with connect(path) as con:
        row = con.execute("SELECT * FROM findings WHERE id=?", (finding_id,)).fetchone()
        return dict(row) if row else None


def versions(finding_id: str, path: Path | str = DB_PATH) -> pd.DataFrame:
    with connect(path) as con:
        return pd.read_sql_query(
            "SELECT * FROM finding_versions WHERE finding_id=? ORDER BY version_id DESC", con, params=(finding_id,)
        )


def list_sources(path: Path | str = DB_PATH) -> pd.DataFrame:
    with connect(path) as con:
        return pd.read_sql_query("SELECT * FROM sources ORDER BY jurisdiction,name", con)


def upsert_source(record: dict, path: Path | str = DB_PATH):
    clean = {c: record.get(c) for c in SOURCE_COLUMNS}
    clean["active"] = int(bool(clean.get("active")))
    clean["discovered_automatically"] = int(bool(clean.get("discovered_automatically")))
    with connect(path) as con:
        ph = ",".join(["?"] * len(SOURCE_COLUMNS))
        updates = ",".join([f"{c}=excluded.{c}" for c in SOURCE_COLUMNS[1:]])
        con.execute(
            f"INSERT INTO sources ({','.join(SOURCE_COLUMNS)}) VALUES ({ph}) ON CONFLICT(id) DO UPDATE SET {updates}",
            [clean[c] for c in SOURCE_COLUMNS],
        )


def get_runtime_state(key: str, default: str | None = None, path: Path | str = DB_PATH) -> str | None:
    with connect(path) as con:
        row = con.execute("SELECT value FROM runtime_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_runtime_state(key: str, value: str, path: Path | str = DB_PATH):
    with connect(path) as con:
        con.execute(
            "INSERT INTO runtime_state (key,value,updated_at) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, _now()),
        )
