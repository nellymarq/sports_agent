# pipeline/event_pipeline.py
# Unified event pipeline for orchestrator + specialists (async).

from __future__ import annotations
from typing import Optional, Dict, Any

from event_utils import (
    get_event_by_code,
    get_unified_next_event,
    get_unified_event,
)

from data.events_fusion import build_unified_event
from data.fighter_history_service import FighterHistoryService
from specialists.event_context_builder import EventContextBuilder
from specialists.prediction_features import PredictionFeatureBuilder


class EventPipeline:
    """
    End-to-end event pipeline (async):
      - loads legacy event (baseline + patches)
      - builds unified event via fusion layer
      - enriches with fighter history
      - produces specialist-ready payloads
    """

    def __init__(self):
        self.history_service = FighterHistoryService()
        self.context_builder = EventContextBuilder()
        self.feature_builder = PredictionFeatureBuilder()

    async def load_unified_event(self, event_id: str):
        legacy = await get_unified_event(event_id)
        if not legacy:
            return None

        unified = await build_unified_event(event_id, legacy_seed=legacy)
        enriched = self.history_service.enrich_event(unified)
        return enriched

    async def load_unified_next_event(self):
        legacy = await get_unified_next_event()
        if not legacy:
            return None

        event_id = legacy.get("id")
        if not event_id:
            return None

        unified = await build_unified_event(event_id, legacy_seed=legacy)
        enriched = self.history_service.enrich_event(unified)
        return enriched

    async def build_metadata_payload(self, event_id: str) -> Optional[Dict[str, Any]]:
        ev = await self.load_unified_event(event_id)
        if not ev:
            return None
        return self.context_builder.build_context(ev)

    async def build_next_event_metadata_payload(self) -> Optional[Dict[str, Any]]:
        ev = await self.load_unified_next_event()
        if not ev:
            return None
        return self.context_builder.build_context(ev)

    async def build_prediction_payload(self, event_id: str) -> Optional[Dict[str, Any]]:
        ev = await self.load_unified_event(event_id)
        if not ev:
            return None
        return self.feature_builder.build_event_features(ev)

    async def build_next_event_prediction_payload(self) -> Optional[Dict[str, Any]]:
        ev = await self.load_unified_next_event()
        if not ev:
            return None
        return self.feature_builder.build_event_features(ev)
