# data/fighter_canonical.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import hashlib

from data.history_client import HistoryDB
from data.events_schema import FighterRef


@dataclass
class CanonicalFighter:
    fighter_id: str
    canonical_name: str
    nickname: Optional[str] = None
    metadata: Dict[str, Any] = None


class FighterCanonicalizer:
    """
    Lightweight canonicalization layer:
    - maps raw names from different sources to a stable fighter_id
    - can be backed by simple hashing + optional overrides
    - integrates with HistoryDB for enrichment
    """

    def __init__(self, history_db: Optional[HistoryDB] = None):
        self.history_db = history_db or HistoryDB()
        # Optional: in-memory overrides for known tricky cases
        self.overrides: Dict[str, str] = {}

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(name.strip().lower().split())

    @staticmethod
    def _hash_name(name: str) -> str:
        norm = FighterCanonicalizer._normalize_name(name)
        return hashlib.sha1(norm.encode("utf-8")).hexdigest()

    def register_override(self, raw_name: str, fighter_id: str):
        self.overrides[self._normalize_name(raw_name)] = fighter_id

    def resolve_fighter_id(self, raw_name: str) -> str:
        norm = self._normalize_name(raw_name)
        if norm in self.overrides:
            return self.overrides[norm]
        return self._hash_name(norm)

    def build_canonical_fighter(self, raw_name: str, extra: Optional[Dict[str, Any]] = None) -> CanonicalFighter:
        fighter_id = self.resolve_fighter_id(raw_name)
        extra = extra or {}
        return CanonicalFighter(
            fighter_id=fighter_id,
            canonical_name=raw_name,
            nickname=extra.get("nickname"),
            metadata=extra,
        )

    def to_fighter_ref(self, raw_name: str, extra: Optional[Dict[str, Any]] = None) -> FighterRef:
        cf = self.build_canonical_fighter(raw_name, extra)
        return FighterRef(
            fighter_id=cf.fighter_id,
            name=cf.canonical_name,
            nickname=cf.metadata.get("nickname"),
            record=cf.metadata.get("record"),
            stance=cf.metadata.get("stance"),
            height=cf.metadata.get("height"),
            reach=cf.metadata.get("reach"),
            age=cf.metadata.get("age"),
            camp=cf.metadata.get("camp"),
            metadata=cf.metadata,
        )

    def get_history_summary(self, fighter_id: str) -> Dict[str, Any]:
        """
        Returns a compact summary suitable for specialists:
        - last_5: list of recent fights
        - streak: "W3", "L2", etc.
        - method_distribution, round_distribution
        """
        fights = self.history_db.get_fighter_history(fighter_id)
        if not fights:
            return {
                "last_5": [],
                "streak": None,
                "method_distribution": {},
                "round_distribution": {},
            }

        last_5 = fights[:5]
        method_dist: Dict[str, int] = {}
        round_dist: Dict[str, int] = {}
        streak = None

        # compute streak from most recent backwards
        current = 0
        current_type = None
        for f in fights:
            res = (f.get("result") or "").upper()
            if res in ("WIN", "LOSS"):
                if current_type is None:
                    current_type = res
                    current = 1
                elif res == current_type:
                    current += 1
                else:
                    break
        if current_type:
            streak = f"{current_type[0]}{current}"

        for f in fights:
            method = f.get("method") or "UNKNOWN"
            rnd = str(f.get("round") or "UNK")
            method_dist[method] = method_dist.get(method, 0) + 1
            round_dist[rnd] = round_dist.get(rnd, 0) + 1

        return {
            "last_5": last_5,
            "streak": streak,
            "method_distribution": method_dist,
            "round_distribution": round_dist,
        }

    def get_pair_shared_opponents(self, fighter_a_id: str, fighter_b_id: str) -> Dict[str, Any]:
        shared_ids = self.history_db.get_shared_opponents(fighter_a_id, fighter_b_id)
        return {
            "shared_opponent_ids": shared_ids,
        }
