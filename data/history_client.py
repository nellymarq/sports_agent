# data/history_client.py

import sqlite3
import time
from typing import List, Dict, Any, Optional

DB_PATH = "data/fighter_history.db"


class HistoryDB:
    def __init__(self, path: str = DB_PATH):
        self.path = path

    def _connect(self):
        return sqlite3.connect(self.path)

    # ------------------------------
    # Schema initialization
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
