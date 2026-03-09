# specialists/event_context_builder.py

from __future__ import annotations
from typing import Dict, Any

from data.events_schema import Event
from data.fighter_history_service import FighterHistoryService


class EventContextBuilder:
    """
    Builds rich, structured context for specialists from a unified Event:
    - fighter histories
    - odds
    - bout ordering
    """

    def __init__(self):
        self.history_service = FighterHistoryService()

    def build_context(self, event: Event) -> Dict[str, Any]:
        # Enrich event with history in-place
        event = self.history_service.enrich_event(event)
        return self.history_service.build_specialist_payload(event)
