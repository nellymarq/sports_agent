# data/events_schema.py

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import time

EVENT_SCHEMA_VERSION = "2.0.0"


def _now() -> float:
    return time.time()


@dataclass
class FighterRef:
    """Reference to a fighter in an event context."""
    fighter_id: Optional[str] = None          # canonical ID (if known)
    name: str = ""                            # display name
    rank: Optional[str] = None
    is_champion: bool = False
    record: Optional[str] = None              # "24-3-0"
    stance: Optional[str] = None
    height: Optional[str] = None
    reach: Optional[str] = None
    age: Optional[int] = None
    camp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoutOdds:
    """Odds + market data for a single bout."""
    favorite: Optional[str] = None
    underdog: Optional[str] = None
    favorite_odds: Optional[float] = None     # e.g. -180
    underdog_odds: Optional[float] = None     # e.g. +150
    implied_prob_favorite: Optional[float] = None
    implied_prob_underdog: Optional[float] = None
    markets: Dict[str, Any] = field(default_factory=dict)  # DK, FD, Polymarket, etc.


@dataclass
class Bout:
    """Single fight on a card."""
    bout_id: str
    order: int                                # 1 = main event, etc.
    weight_class: Optional[str] = None
    is_title_fight: bool = False
    is_main_event: bool = False
    is_co_main_event: bool = False
    fighters: List[FighterRef] = field(default_factory=list)
    odds: Optional[BoutOdds] = None
    topology: Dict[str, Any] = field(default_factory=dict)  # 5‑round/3‑round, cage size, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventFreshness:
    """Tracks when and how this event was last updated."""
    last_updated: float
    sources: Dict[str, float]                 # source_name -> timestamp


@dataclass
class EventProvenance:
    """Tracks raw source payloads and decisions."""
    raw_sources: Dict[str, Any] = field(default_factory=dict)
    merge_notes: List[str] = field(default_factory=list)


@dataclass
class Event:
    """Unified, multi‑source event model."""
    id: str                                   # "ufc_313"
    code: str                                 # "UFC 313"
    name: str
    date: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None            # backward‑compat alias
    timezone: Optional[str] = None
    broadcast: Optional[str] = None           # "ESPN+", "PPV", etc.
    status: Optional[str] = None              # "scheduled", "completed", "cancelled"
    main_event: Optional[Bout] = None
    co_main_event: Optional[Bout] = None
    card: List[Bout] = field(default_factory=list)
    freshness: Optional[EventFreshness] = None
    provenance: EventProvenance = field(default_factory=EventProvenance)
    schema_version: str = EVENT_SCHEMA_VERSION
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------
    # Backward‑compatible helpers
    # ------------------------------
    @staticmethod
    def from_legacy_dict(data: Dict[str, Any]) -> "Event":
        """
        Build an Event from your current minimal JSON schema.
        This keeps existing events.json perfectly valid.
        """
        ev_id = data.get("id", "")
        code = data.get("code", ev_id)
        name = data.get("name", code)

        # legacy main/co-main structure: {"fighters": []}
        main = data.get("main_event") or {}
        co_main = data.get("co_main_event") or {}

        def _legacy_bout(block: Dict[str, Any], order: int, is_main: bool, is_co: bool) -> Optional[Bout]:
            fighters = [
                FighterRef(name=f) if isinstance(f, str) else FighterRef(name=f.get("name", ""))
                for f in block.get("fighters", [])
            ]
            if not fighters:
                return None
            return Bout(
                bout_id=f"{ev_id}_bout_{order}",
                order=order,
                is_main_event=is_main,
                is_co_main_event=is_co,
                fighters=fighters,
            )

        main_bout = _legacy_bout(main, 1, True, False)
        co_main_bout = _legacy_bout(co_main, 2, False, True)

        card_bouts: List[Bout] = []
        for i, b in enumerate(data.get("card", []), start=3):
            fighters = [
                FighterRef(name=f) if isinstance(f, str) else FighterRef(name=f.get("name", ""))
                for f in b.get("fighters", [])
            ]
            card_bouts.append(
                Bout(
                    bout_id=f"{ev_id}_bout_{i}",
                    order=i,
                    weight_class=b.get("weight_class"),
                    fighters=fighters,
                )
            )

        return Event(
            id=ev_id,
            code=code,
            name=name,
            location=data.get("location") or None,
            main_event=main_bout,
            co_main_event=co_main_bout,
            card=card_bouts,
            freshness=None,
        )

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Export a minimal view compatible with your existing events.json structure.
        Useful if you want to keep writing the old format somewhere.
        """
        def _bout_to_legacy(b: Optional[Bout]) -> Dict[str, Any]:
            if not b:
                return {"fighters": []}
            return {"fighters": [f.name for f in b.fighters]}

        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "location": self.location or "",
            "main_event": _bout_to_legacy(self.main_event),
            "co_main_event": _bout_to_legacy(self.co_main_event),
            "card": [
                {"fighters": [f.name for f in b.fighters]}
                for b in self.card
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
