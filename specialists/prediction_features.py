# specialists/prediction_features.py

from __future__ import annotations
from typing import Dict, Any, List, Optional

from data.events_schema import Event, Bout, FighterRef
from data.fighter_history_service import FighterHistoryService


class PredictionFeatureBuilder:
    """
    Builds structured, model-friendly features for prediction specialists:
    - odds + implied probabilities
    - recent form (last_5, streak)
    - method/round distributions
    - shared opponents
    """

    def __init__(self):
        self.history_service = FighterHistoryService()

    def _fighter_features(self, f: FighterRef) -> Dict[str, Any]:
        hist = (f.metadata or {}).get("history_summary", {})
        return {
            "fighter_id": f.fighter_id,
            "name": f.name,
            "record": f.record,
            "streak": hist.get("streak"),
            "method_distribution": hist.get("method_distribution", {}),
            "round_distribution": hist.get("round_distribution", {}),
            "last_5": hist.get("last_5", []),
        }

    def _bout_features(self, bout: Bout) -> Dict[str, Any]:
        fighters = [self._fighter_features(f) for f in bout.fighters]
        odds = bout.odds.__dict__ if bout.odds else {}

        shared_opponents: Optional[Dict[str, Any]] = None
        if len(bout.fighters) == 2:
            fa, fb = bout.fighters
            shared_opponents = self.history_service.canon.get_pair_shared_opponents(
                fa.fighter_id, fb.fighter_id
            )

        return {
            "bout_id": bout.bout_id,
            "order": bout.order,
            "weight_class": bout.weight_class,
            "is_title_fight": bout.is_title_fight,
            "fighters": fighters,
            "odds": odds,
            "shared_opponents": shared_opponents,
        }

    def build_event_features(self, event: Event) -> Dict[str, Any]:
        event = self.history_service.enrich_event(event)

        def _maybe(b: Optional[Bout]) -> Optional[Dict[str, Any]]:
            return self._bout_features(b) if b else None

        return {
            "event_id": event.id,
            "code": event.code,
            "name": event.name,
            "date": event.date,
            "location": event.location,
            "main_event": _maybe(event.main_event),
            "co_main_event": _maybe(event.co_main_event),
            "card": [self._bout_features(b) for b in event.card],
        }
