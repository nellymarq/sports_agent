# data/elo_rating.py
# ELO-based power rating system for UFC fighters.
# Inspired by FiveThirtyEight's approach adapted for MMA.

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date


# Default starting ELO
DEFAULT_ELO = 1500

# K-factor settings (how much a single fight moves ratings)
K_BASE = 40          # Base K-factor
K_FINISH_BONUS = 8   # Extra K for finishes (KO/TKO/Sub)
K_TITLE_BONUS = 6    # Extra K for title fights
K_EARLY_CAREER = 12  # Extra K for first 5 fights (ratings converge faster)

# Method multipliers for margin-of-victory adjustment
METHOD_MULTIPLIERS = {
    "ko": 1.3,
    "tko": 1.25,
    "submission": 1.2,
    "dq": 1.0,
    "decision": 1.0,
    "unanimous": 1.0,
    "split": 0.9,      # Close fight = smaller update
    "majority": 0.95,
}

# Inactivity decay: lose rating points per year inactive
INACTIVITY_DECAY_PER_YEAR = 30
INACTIVITY_THRESHOLD_DAYS = 365


def expected_score(rating_a: float, rating_b: float) -> float:
    """Calculate expected win probability for fighter A given both ratings."""
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400))


def get_method_multiplier(method: str) -> float:
    """Get margin-of-victory multiplier from fight method string."""
    method_lower = (method or "").lower()
    # Check specific patterns first (order matters: tko before ko, split before decision)
    if "split" in method_lower:
        return METHOD_MULTIPLIERS["split"]
    if "majority" in method_lower:
        return METHOD_MULTIPLIERS["majority"]
    if "tko" in method_lower:
        return METHOD_MULTIPLIERS["tko"]
    if "ko" in method_lower:
        return METHOD_MULTIPLIERS["ko"]
    if "sub" in method_lower:
        return METHOD_MULTIPLIERS["submission"]
    if "dec" in method_lower or "unanimous" in method_lower:
        return METHOD_MULTIPLIERS["decision"]
    if "dq" in method_lower:
        return METHOD_MULTIPLIERS["dq"]
    return 1.0


def compute_k_factor(
    fighter_fight_count: int,
    method: str = "",
    is_title_fight: bool = False,
) -> float:
    """
    Compute adaptive K-factor based on fight context.
    Higher K = bigger rating swings.
    """
    k = K_BASE

    # Early career: ratings should move faster
    if fighter_fight_count < 5:
        k += K_EARLY_CAREER

    # Finishes are more decisive
    method_lower = (method or "").lower()
    if any(m in method_lower for m in ("ko", "tko", "sub")):
        k += K_FINISH_BONUS

    # Title fights carry more weight
    if is_title_fight:
        k += K_TITLE_BONUS

    return k


def apply_inactivity_decay(
    rating: float,
    last_fight_date: Optional[str],
    current_date: Optional[date] = None,
) -> float:
    """Apply inactivity decay to a fighter's rating."""
    if not last_fight_date:
        return rating

    try:
        last_dt = datetime.strptime(last_fight_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return rating

    today = current_date or date.today()
    days_inactive = (today - last_dt).days

    if days_inactive > INACTIVITY_THRESHOLD_DAYS:
        years_inactive = days_inactive / 365.25
        decay = INACTIVITY_DECAY_PER_YEAR * (years_inactive - 1.0)
        # Don't decay below floor
        return max(rating - decay, DEFAULT_ELO - 200)

    return rating


def update_elo(
    rating_winner: float,
    rating_loser: float,
    method: str = "",
    is_title_fight: bool = False,
    winner_fight_count: int = 10,
    loser_fight_count: int = 10,
) -> Tuple[float, float]:
    """
    Update ELO ratings after a fight.

    Returns:
        (new_winner_rating, new_loser_rating)
    """
    expected_w = expected_score(rating_winner, rating_loser)
    expected_l = 1.0 - expected_w

    method_mult = get_method_multiplier(method)

    k_winner = compute_k_factor(winner_fight_count, method, is_title_fight)
    k_loser = compute_k_factor(loser_fight_count, method, is_title_fight)

    # Winner gains: scaled by method multiplier and surprise factor
    new_winner = rating_winner + k_winner * method_mult * (1 - expected_w)
    # Loser loses: also scaled
    new_loser = rating_loser + k_loser * method_mult * (0 - expected_l)

    return round(new_winner, 1), round(new_loser, 1)


class ELORatingSystem:
    """
    Maintains ELO ratings for all fighters.
    Can be initialized from fight history and updated incrementally.
    """

    def __init__(self):
        self.ratings: Dict[str, float] = {}
        self.fight_counts: Dict[str, int] = {}
        self.last_fight_dates: Dict[str, str] = {}
        self.rating_history: Dict[str, List[Dict[str, Any]]] = {}

    def get_rating(self, fighter_id: str) -> float:
        return self.ratings.get(fighter_id, DEFAULT_ELO)

    def get_fight_count(self, fighter_id: str) -> int:
        return self.fight_counts.get(fighter_id, 0)

    def process_fight(
        self,
        winner_id: str,
        loser_id: str,
        method: str = "",
        fight_date: str = "",
        is_title_fight: bool = False,
        event_name: str = "",
    ) -> Tuple[float, float]:
        """
        Process a single fight result and update ratings.

        Returns:
            (new_winner_rating, new_loser_rating)
        """
        old_winner = self.get_rating(winner_id)
        old_loser = self.get_rating(loser_id)

        new_winner, new_loser = update_elo(
            old_winner,
            old_loser,
            method=method,
            is_title_fight=is_title_fight,
            winner_fight_count=self.get_fight_count(winner_id),
            loser_fight_count=self.get_fight_count(loser_id),
        )

        self.ratings[winner_id] = new_winner
        self.ratings[loser_id] = new_loser

        self.fight_counts[winner_id] = self.get_fight_count(winner_id) + 1
        self.fight_counts[loser_id] = self.get_fight_count(loser_id) + 1

        if fight_date:
            self.last_fight_dates[winner_id] = fight_date
            self.last_fight_dates[loser_id] = fight_date

        # Record history
        entry = {
            "date": fight_date,
            "event": event_name,
            "method": method,
        }
        for fid, old_r, new_r, result in [
            (winner_id, old_winner, new_winner, "W"),
            (loser_id, old_loser, new_loser, "L"),
        ]:
            if fid not in self.rating_history:
                self.rating_history[fid] = []
            self.rating_history[fid].append({
                **entry,
                "old_rating": old_r,
                "new_rating": new_r,
                "result": result,
                "change": round(new_r - old_r, 1),
            })

        return new_winner, new_loser

    def process_fights_batch(
        self, fights: List[Dict[str, Any]]
    ) -> None:
        """
        Process a batch of fights sorted by date ascending.

        Each fight dict should have:
            winner_id, loser_id, method, date, is_title_fight, event_name
        """
        # Sort by date to ensure chronological processing
        sorted_fights = sorted(fights, key=lambda f: f.get("date", ""))

        for fight in sorted_fights:
            self.process_fight(
                winner_id=fight["winner_id"],
                loser_id=fight["loser_id"],
                method=fight.get("method", ""),
                fight_date=fight.get("date", ""),
                is_title_fight=fight.get("is_title_fight", False),
                event_name=fight.get("event_name", ""),
            )

    def apply_inactivity_decay_all(
        self, current_date: Optional[date] = None
    ) -> int:
        """Apply inactivity decay to all fighters. Returns count of decayed."""
        decayed = 0
        for fid in list(self.ratings.keys()):
            old = self.ratings[fid]
            new = apply_inactivity_decay(
                old, self.last_fight_dates.get(fid), current_date
            )
            if new != old:
                self.ratings[fid] = new
                decayed += 1
        return decayed

    def get_rankings(
        self,
        weight_class: Optional[str] = None,
        top_n: int = 15,
        fighter_names: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get ranked fighter list by ELO rating.

        Args:
            weight_class: Filter by weight class (requires fight history context)
            top_n: Number of fighters to return
            fighter_names: Optional mapping of fighter_id -> name
        """
        names = fighter_names or {}
        ranked = sorted(
            self.ratings.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        return [
            {
                "rank": i + 1,
                "fighter_id": fid,
                "name": names.get(fid, fid),
                "rating": rating,
                "fights": self.get_fight_count(fid),
                "trend": self._get_trend(fid),
            }
            for i, (fid, rating) in enumerate(ranked)
        ]

    def _get_trend(self, fighter_id: str) -> str:
        """Get recent rating trend arrow."""
        history = self.rating_history.get(fighter_id, [])
        if len(history) < 2:
            return "—"
        last_two = history[-2:]
        total_change = sum(h["change"] for h in last_two)
        if total_change > 10:
            return "↑↑"
        elif total_change > 0:
            return "↑"
        elif total_change < -10:
            return "↓↓"
        elif total_change < 0:
            return "↓"
        return "→"

    def get_matchup_prediction(
        self, fighter_a_id: str, fighter_b_id: str
    ) -> Dict[str, Any]:
        """
        Predict fight outcome using ELO ratings.
        Returns expected win probability for each fighter.
        """
        rating_a = self.get_rating(fighter_a_id)
        rating_b = self.get_rating(fighter_b_id)

        prob_a = expected_score(rating_a, rating_b)
        prob_b = 1.0 - prob_a

        diff = abs(rating_a - rating_b)

        return {
            "fighter_a_rating": rating_a,
            "fighter_b_rating": rating_b,
            "rating_diff": round(rating_a - rating_b, 1),
            "fighter_a_win_prob": round(prob_a, 4),
            "fighter_b_win_prob": round(prob_b, 4),
            "confidence": _rating_diff_to_confidence(diff),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for caching/persistence."""
        return {
            "ratings": self.ratings,
            "fight_counts": self.fight_counts,
            "last_fight_dates": self.last_fight_dates,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ELORatingSystem":
        """Restore from serialized state."""
        system = cls()
        system.ratings = data.get("ratings", {})
        system.fight_counts = data.get("fight_counts", {})
        system.last_fight_dates = data.get("last_fight_dates", {})
        return system


def _rating_diff_to_confidence(diff: float) -> str:
    """Convert rating difference to confidence tier."""
    if diff >= 200:
        return "very_high"
    elif diff >= 100:
        return "high"
    elif diff >= 50:
        return "moderate"
    elif diff >= 20:
        return "slight"
    else:
        return "toss_up"


def elo_probability_to_american_odds(prob: float) -> str:
    """Convert ELO win probability to American odds format."""
    if prob <= 0 or prob >= 1:
        return "N/A"
    if prob >= 0.5:
        odds = -round(prob / (1 - prob) * 100)
        return str(odds)
    else:
        odds = round((1 - prob) / prob * 100)
        return f"+{odds}"
