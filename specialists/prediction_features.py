# specialists/prediction_features.py

from __future__ import annotations
from typing import Dict, Any, List, Optional

from data.events_schema import Event, Bout, FighterRef
from data.fighter_history_service import FighterHistoryService
from data.style_classifier import classify_style, classify_matchup
from data.aging_curve import full_age_analysis, age_adjustment
from data.cage_control import analyze_clinch_profile, compute_octagon_control_score, analyze_clinch_matchup, predict_fight_location


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
        meta = f.metadata or {}
        stats = meta.get("stats", {})

        features: Dict[str, Any] = {
            "fighter_id": f.fighter_id,
            "name": f.name,
            "record": f.record,
            "streak": hist.get("streak"),
            "method_distribution": hist.get("method_distribution", {}),
            "round_distribution": hist.get("round_distribution", {}),
            "last_5": hist.get("last_5", []),
        }

        # Style classification
        try:
            if stats:
                features["style"] = classify_style(stats)
        except Exception:
            pass

        # Aging curve analysis
        try:
            age = meta.get("age")
            if age is not None:
                age = int(age)
                features["aging"] = full_age_analysis(
                    age=age,
                    weight_class=meta.get("weight_class"),
                    record=f.record or "",
                    fight_history=hist.get("fight_history"),
                    fighter_stats=stats or None,
                    ko_losses=int(meta.get("ko_losses", 0)),
                    total_fights=int(meta.get("total_fights", 0)),
                    years_since_last_ko_loss=meta.get("years_since_last_ko_loss"),
                    streak_type=hist.get("streak", {}).get("type", "") if isinstance(hist.get("streak"), dict) else "",
                    streak_count=int(hist.get("streak", {}).get("count", 0)) if isinstance(hist.get("streak"), dict) else 0,
                    ufc_fight_count=int(meta.get("ufc_fight_count", 0)),
                )
        except Exception:
            pass

        # Clinch profile
        try:
            if stats:
                features["clinch_profile"] = analyze_clinch_profile(stats)
        except Exception:
            pass

        # Octagon control
        try:
            if stats:
                features["octagon_control"] = compute_octagon_control_score(stats)
        except Exception:
            pass

        return features

    def _bout_features(self, bout: Bout) -> Dict[str, Any]:
        fighters = [self._fighter_features(f) for f in bout.fighters]
        odds = bout.odds.__dict__ if bout.odds else {}

        shared_opponents: Optional[Dict[str, Any]] = None
        if len(bout.fighters) == 2:
            fa, fb = bout.fighters
            shared_opponents = self.history_service.canon.get_pair_shared_opponents(
                fa.fighter_id, fb.fighter_id
            )

        result: Dict[str, Any] = {
            "bout_id": bout.bout_id,
            "order": bout.order,
            "weight_class": bout.weight_class,
            "is_title_fight": bout.is_title_fight,
            "fighters": fighters,
            "odds": odds,
            "shared_opponents": shared_opponents,
        }

        # Matchup-level features (require exactly 2 fighters with stats)
        if len(bout.fighters) == 2:
            fa, fb = bout.fighters
            meta_a = fa.metadata or {}
            meta_b = fb.metadata or {}
            stats_a = meta_a.get("stats", {})
            stats_b = meta_b.get("stats", {})

            # Style matchup classification
            try:
                if stats_a and stats_b:
                    result["style_matchup"] = classify_matchup(stats_a, stats_b)
            except Exception:
                pass

            # Clinch matchup analysis
            try:
                if stats_a and stats_b:
                    result["clinch_matchup"] = analyze_clinch_matchup(stats_a, stats_b)
            except Exception:
                pass

            # Fight location prediction
            try:
                if stats_a and stats_b:
                    result["fight_location"] = predict_fight_location(stats_a, stats_b)
            except Exception:
                pass

            # Age adjustment between fighters
            try:
                age_a = meta_a.get("age")
                age_b = meta_b.get("age")
                if age_a is not None and age_b is not None:
                    age_a = int(age_a)
                    age_b = int(age_b)
                    # Use career phases from fighter features if available
                    phase_a = None
                    phase_b = None
                    if fighters[0].get("aging"):
                        phase_a = fighters[0]["aging"].get("career_phase", {}).get("phase")
                    if fighters[1].get("aging"):
                        phase_b = fighters[1]["aging"].get("career_phase", {}).get("phase")
                    result["age_adjustment"] = age_adjustment(
                        age_a=age_a,
                        age_b=age_b,
                        weight_class=bout.weight_class,
                        phase_a=phase_a,
                        phase_b=phase_b,
                    )
            except Exception:
                pass

        return result

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
