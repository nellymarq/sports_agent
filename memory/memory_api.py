# memory/memory_api.py

from __future__ import annotations
from typing import List, Dict, Any
from data.metadata import Evidence, SCHEMA_VERSION
import time
import hashlib


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MemoryStore:
    def __init__(self):
        self.long_term: List[Dict[str, Any]] = []
        self.short_term: List[Dict[str, Any]] = []
        self.evidence: List[Evidence] = []
        self.specialist_notes: Dict[str, List[Dict[str, Any]]] = {}

    def write_long_term(self, item: Dict[str, Any]):
        item["timestamp"] = time.time()
        item["schema_version"] = SCHEMA_VERSION
        item["hash"] = _hash(str(item))
        self.long_term.append(item)

    def write_short_term(self, item: Dict[str, Any]):
        item["timestamp"] = time.time()
        item["schema_version"] = SCHEMA_VERSION
        self.short_term.append(item)

    def write_evidence(self, ev: Evidence):
        self.evidence.append(ev)

    def write_specialist_note(self, specialist: str, note: Dict[str, Any]):
        note["timestamp"] = time.time()
        note["schema_version"] = SCHEMA_VERSION
        if specialist not in self.specialist_notes:
            self.specialist_notes[specialist] = []
        self.specialist_notes[specialist].append(note)

    def get_recent_short_term(self, limit: int = 10) -> List[Dict[str, Any]]:
        return sorted(self.short_term, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_long_term(self) -> List[Dict[str, Any]]:
        return self.long_term

    def get_evidence(self) -> List[Evidence]:
        return self.evidence

    def get_specialist_history(self, specialist: str) -> List[Dict[str, Any]]:
        return self.specialist_notes.get(specialist, [])

    def find_similar(self, text: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        return []

    def cluster_topics(self) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    def dedupe_long_term(self):
        seen = set()
        unique = []
        for item in self.long_term:
            if item["hash"] not in seen:
                seen.add(item["hash"])
                unique.append(item)
        self.long_term = unique

    def decay_long_term(self, threshold_seconds: float):
        now = time.time()
        self.long_term = [
            item for item in self.long_term
            if now - item["timestamp"] < threshold_seconds
        ]
