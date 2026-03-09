# data/fighter_history_service.py

from __future__ import annotations
from typing import Dict, Any, Optional

from data.history_client import HistoryDB
from data.fighter_canonical import FighterCanonicalizer
from data.events_schema import Event, Bout, FighterRef


class FighterHistoryService:
    """
    High-level service that:
    - canonicalizes fighter names in Events
    - enriches them with history summaries
    """

    def __init__(self, history_db: Optional[HistoryDB] = None):
        self.history_db = history_db or HistoryDB()
        self.canon = FighterCanonicalizer(self.history_db)

    def _enrich_fighter_ref(self, f: FighterRef) -> FighterRef:
        if not f.name:
            return f

        fighter_id = f.fighter_id or self.canon.resolve_fighter_id(f.name)
        summary = self.canon.get_history_summary(fighter_id)

        f.fighter_id = fighter_id
        f.metadata = {
            **(f.metadata or {}),
            "history_summary": summary,
        }
        return f

    def enrich_bout(self, bout: Bout) -> Bout:
        bout.fighters = [self._enrich_fighter_ref(f) for f in bout.fighters]
        return bout

    def enrich_event(self, event: Event) -> Event:
        if event.main_event:
            event.main_event = self.enrich_bout(event.main_event)
        if event.co_main_event:
            event.co_main_event = self.enrich_bout(event.co_main_event)
        event.card = [self.enrich_bout(b) for b in event.card]
        return event

    def build_specialist_payload(self, event: Event) -> Dict[str, Any]:
        """
        Compact, specialist-friendly view of an event with history attached.
        """
        def _fighter_payload(f: FighterRef) -> Dict[str, Any]:
            return {
                "fighter_id": f.fighter_id,
                "name": f.name,
                "rank": f.rank,
                "is_champion": f.is_champion,
                "record": f.record,
                "history_summary": (f.metadata or {}).get("history_summary", {}),
            }

        def _bout_payload(b: Bout) -> Dict[str, Any]:
            return {
                "bout_id": b.bout_id,
                "order": b.order,
                "weight_class": b.weight_class,
                "is_title_fight": b.is_title_fight,
                "is_main_event": b.is_main_event,
                "is_co_main_event": b.is_co_main_event,
                "fighters": [_fighter_payload(f) for f in b.fighters],
                "odds": b.odds.__dict__ if b.odds else None,
            }

        return {
            "event_id": event.id,
            "code": event.code,
            "name": event.name,
            "date": event.date,
            "location": event.location,
            "main_event": _bout_payload(event.main_event) if event.main_event else None,
            "co_main_event": _bout_payload(event.co_main_event) if event.co_main_event else None,
            "card": [_bout_payload(b) for b in event.card],
        }
