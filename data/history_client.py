# data/history_client.py

import sqlite3
import time
import logging
from typing import List, Dict, Any, Optional

DB_PATH = "data/fighter_history.db"
SCHEMA_VERSION = 2

_logger = logging.getLogger("history_client")

# Schema migrations keyed by target version.
# Each migration runs only if current version < target.
_MIGRATIONS = {
    1: [
        """CREATE TABLE IF NOT EXISTS fighters (
            fighter_id TEXT PRIMARY KEY,
            canonical_name TEXT,
            nickname TEXT,
            height TEXT,
            reach TEXT,
            stance TEXT,
            dob TEXT,
            country TEXT,
            updated_at REAL
        );""",
        """CREATE TABLE IF NOT EXISTS fights (
            fight_id TEXT PRIMARY KEY,
            fighter_id TEXT,
            opponent_id TEXT,
            event_id TEXT,
            event_name TEXT,
            date TEXT,
            weight_class TEXT,
            result TEXT,
            method TEXT,
            round INTEGER,
            time TEXT,
            source TEXT,
            updated_at REAL
        );""",
    ],
    2: [
        """CREATE INDEX IF NOT EXISTS idx_fights_fighter ON fights(fighter_id);""",
        """CREATE INDEX IF NOT EXISTS idx_fights_opponent ON fights(opponent_id);""",
    ],
}


class HistoryDB:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._ensure_schema()

    def _connect(self):
        return sqlite3.connect(self.path)

    # ------------------------------
    # Schema versioning
    # ------------------------------
    def _get_schema_version(self, conn) -> int:
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT)")
            row = conn.execute("SELECT value FROM schema_meta WHERE key='version'").fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def _set_schema_version(self, conn, version: int):
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
            (str(version),),
        )

    def _ensure_schema(self):
        with self._connect() as conn:
            current = self._get_schema_version(conn)
            for target_version in sorted(_MIGRATIONS.keys()):
                if current < target_version:
                    _logger.info(f"Migrating history DB: v{current} -> v{target_version}")
                    for stmt in _MIGRATIONS[target_version]:
                        conn.execute(stmt)
                    current = target_version
            self._set_schema_version(conn, current)

    # ------------------------------
    # Schema initialization (legacy compat)
    # ------------------------------
    def init_schema(self, schema_path: str = "data/history_schema.sql"):
        with open(schema_path, "r") as f:
            schema = f.read()
        with self._connect() as conn:
            conn.executescript(schema)

    # ------------------------------
    # Fighter operations
    # ------------------------------
    def upsert_fighter(self, fighter: Dict[str, Any]):
        fighter["updated_at"] = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO fighters (
                    fighter_id, canonical_name, nickname, height, reach,
                    stance, dob, country, updated_at
                ) VALUES (
                    :fighter_id, :canonical_name, :nickname, :height, :reach,
                    :stance, :dob, :country, :updated_at
                )
                ON CONFLICT(fighter_id) DO UPDATE SET
                    canonical_name=excluded.canonical_name,
                    nickname=excluded.nickname,
                    height=excluded.height,
                    reach=excluded.reach,
                    stance=excluded.stance,
                    dob=excluded.dob,
                    country=excluded.country,
                    updated_at=excluded.updated_at;
                """,
                fighter,
            )

    def get_fighter(self, fighter_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM fighters WHERE fighter_id = ?", (fighter_id,)
            ).fetchone()
        if not row:
            return None
        cols = [c[0] for c in conn.execute("PRAGMA table_info(fighters)")]
        return dict(zip(cols, row))

    # ------------------------------
    # Fight operations
    # ------------------------------
    def add_fight(self, fight: Dict[str, Any]):
        fight["updated_at"] = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO fights (
                    fight_id, fighter_id, opponent_id, event_id, event_name,
                    date, weight_class, result, method, round, time, source,
                    updated_at
                ) VALUES (
                    :fight_id, :fighter_id, :opponent_id, :event_id, :event_name,
                    :date, :weight_class, :result, :method, :round, :time,
                    :source, :updated_at
                );
                """,
                fight,
            )

    def get_fighter_history(self, fighter_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM fights
                WHERE fighter_id = ?
                ORDER BY date DESC;
                """,
                (fighter_id,),
            ).fetchall()

        if not rows:
            return []

        cols = [c[0] for c in conn.execute("PRAGMA table_info(fights)")]
        return [dict(zip(cols, row)) for row in rows]

    # ------------------------------
    # Shared opponents
    # ------------------------------
    def get_shared_opponents(self, fighter_a: str, fighter_b: str) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT f1.opponent_id
                FROM fights f1
                JOIN fights f2 ON f1.opponent_id = f2.opponent_id
                WHERE f1.fighter_id = ? AND f2.fighter_id = ?
                """,
                (fighter_a, fighter_b),
            ).fetchall()
        return [r[0] for r in rows]
