# data/fighter_profile.py
# Unified fighter profile aggregator: combines UFCStats, history DB,
# and computed analytics into a single fighter profile.

from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from data.style_classifier import classify_style
from data.aging_curve import full_age_analysis, estimate_chin_health
from data.cage_control import analyze_clinch_profile, compute_octagon_control_score


def compute_streak(fights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute current win/loss streak and recent form from fight history.
    Fights should be sorted by date descending (most recent first).
    """
    if not fights:
        return {"current_streak": 0, "streak_type": "none", "form_last_5": ""}

    streak = 0
    streak_type = None

    for f in fights:
        result = (f.get("result") or "").upper().strip()
        if result.startswith("W"):
            if streak_type is None:
                streak_type = "W"
            if streak_type == "W":
                streak += 1
            else:
                break
        elif result.startswith("L"):
            if streak_type is None:
                streak_type = "L"
            if streak_type == "L":
                streak += 1
            else:
                break
        elif result.startswith("D") or result.startswith("NC"):
            break
        else:
            break

    # Form string (last 5)
    form = []
    for f in fights[:5]:
        result = (f.get("result") or "").upper().strip()
        if result.startswith("W"):
            form.append("W")
        elif result.startswith("L"):
            form.append("L")
        elif result.startswith("D"):
            form.append("D")
        else:
            form.append("?")

    return {
        "current_streak": streak,
        "streak_type": streak_type or "none",
        "form_last_5": "".join(form),
    }


def compute_method_distribution(fights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute win/loss method distributions from fight history.
    """
    wins = {"ko_tko": 0, "submission": 0, "decision": 0, "other": 0}
    losses = {"ko_tko": 0, "submission": 0, "decision": 0, "other": 0}

    for f in fights:
        result = (f.get("result") or "").upper().strip()
        method = (f.get("method") or "").lower()

        if "ko" in method or "tko" in method:
            method_key = "ko_tko"
        elif "sub" in method:
            method_key = "submission"
        elif "dec" in method or "unanimous" in method or "split" in method or "majority" in method:
            method_key = "decision"
        else:
            method_key = "other"

        if result.startswith("W"):
            wins[method_key] += 1
        elif result.startswith("L"):
            losses[method_key] += 1

    total_wins = sum(wins.values())
    total_losses = sum(losses.values())

    win_pcts = {}
    if total_wins > 0:
        win_pcts = {k: round(v / total_wins * 100, 1) for k, v in wins.items() if v > 0}

    loss_pcts = {}
    if total_losses > 0:
        loss_pcts = {k: round(v / total_losses * 100, 1) for k, v in losses.items() if v > 0}

    return {
        "wins": wins,
        "losses": losses,
        "win_percentages": win_pcts,
        "loss_percentages": loss_pcts,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "finish_rate": round(
            (wins["ko_tko"] + wins["submission"]) / total_wins * 100, 1
        ) if total_wins > 0 else 0,
        "ko_rate": round(wins["ko_tko"] / total_wins * 100, 1) if total_wins > 0 else 0,
        "sub_rate": round(wins["submission"] / total_wins * 100, 1) if total_wins > 0 else 0,
        "been_finished_rate": round(
            (losses["ko_tko"] + losses["submission"]) / total_losses * 100, 1
        ) if total_losses > 0 else 0,
    }


def compute_round_distribution(fights: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute distribution of fight endings by round."""
    rounds = {}
    for f in fights:
        rnd = f.get("round")
        if rnd is not None:
            rnd_key = f"r{rnd}"
            rounds[rnd_key] = rounds.get(rnd_key, 0) + 1
    return rounds


def compute_activity(fights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute activity metrics: fights per year, layoff."""
    if not fights:
        return {"fights_per_year": 0, "last_fight_days_ago": None, "total_ufc_fights": 0}

    dates = []
    for f in fights:
        d = f.get("date", "")
        if d:
            try:
                dates.append(datetime.strptime(d[:10], "%Y-%m-%d").date())
            except (ValueError, TypeError):
                pass

    if not dates:
        return {"fights_per_year": 0, "last_fight_days_ago": None, "total_ufc_fights": len(fights)}

    dates.sort(reverse=True)
    most_recent = dates[0]
    oldest = dates[-1]

    span_years = max((most_recent - oldest).days / 365.25, 0.5)
    fights_per_year = round(len(dates) / span_years, 1)

    days_since_last = (date.today() - most_recent).days

    return {
        "fights_per_year": fights_per_year,
        "last_fight_days_ago": days_since_last,
        "total_ufc_fights": len(fights),
        "last_fight_date": str(most_recent),
    }


def compute_opposition_quality(fights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate opposition quality from fight context.
    Uses event type (numbered UFC vs Fight Night) as a rough proxy.
    """
    title_fights = 0
    main_events = 0
    numbered_events = 0

    for f in fights:
        event = (f.get("event_name") or "").lower()
        if "title" in (f.get("method") or "").lower() or f.get("is_title_fight"):
            title_fights += 1
        if "ufc " in event and any(c.isdigit() for c in event):
            numbered_events += 1

    return {
        "title_fights": title_fights,
        "numbered_ufc_events": numbered_events,
        "total_fights": len(fights),
    }


def build_fighter_profile(
    name: str,
    ufc_stats: Optional[Dict[str, Any]] = None,
    fight_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a comprehensive fighter profile from all available data sources.

    Args:
        name: Fighter name
        ufc_stats: Data from UFCStatsTool (best_match dict)
        fight_history: Fight history from HistoryDB

    Returns:
        Unified fighter profile dict
    """
    profile: Dict[str, Any] = {"name": name}

    # Physical attributes from UFCStats
    if ufc_stats:
        for key in ["record", "height", "weight", "reach", "stance",
                     "slpm", "str_acc", "sapm", "str_def",
                     "td_avg", "td_acc", "td_def", "sub_avg"]:
            if ufc_stats.get(key):
                profile[key] = ufc_stats[key]

        detail = ufc_stats.get("detail_stats", {})
        if detail.get("recent_fights"):
            profile["recent_fights"] = detail["recent_fights"][:5]
        if detail.get("win_methods"):
            profile["win_methods_raw"] = detail["win_methods"]

    # Fight history analytics
    fights = fight_history or []
    if ufc_stats and not fights:
        # Fall back to recent_fights from UFCStats
        recent = ufc_stats.get("detail_stats", {}).get("recent_fights", [])
        fights = recent

    if fights:
        profile["streak"] = compute_streak(fights)
        profile["method_distribution"] = compute_method_distribution(fights)
        profile["round_distribution"] = compute_round_distribution(fights)
        profile["activity"] = compute_activity(fights)

    # Style classification
    if ufc_stats:
        try:
            profile["style"] = classify_style(ufc_stats)
        except Exception:
            pass

        # Clinch profile
        try:
            profile["clinch_profile"] = analyze_clinch_profile(ufc_stats)
        except Exception:
            pass

        # Octagon control
        try:
            profile["octagon_control"] = compute_octagon_control_score(ufc_stats)
        except Exception:
            pass

    # Aging curve analysis (requires age)
    age = None
    try:
        age_val = (ufc_stats or {}).get("age", "")
        if age_val:
            age = int(str(age_val).strip())
    except (ValueError, TypeError):
        pass

    if age:
        # Count KO losses from method distribution
        ko_losses = 0
        total_fights_count = 0
        if "method_distribution" in profile:
            md = profile["method_distribution"]
            ko_losses = md.get("losses", {}).get("ko_tko", 0)
            total_fights_count = md.get("total_wins", 0) + md.get("total_losses", 0)

        streak_data = profile.get("streak", {})
        record_str = profile.get("record", "")

        try:
            profile["aging"] = full_age_analysis(
                age=age,
                weight_class=(ufc_stats or {}).get("weight_class", ""),
                record=record_str,
                fight_history=fights or None,
                fighter_stats=ufc_stats or {},
                ko_losses=ko_losses,
                total_fights=total_fights_count,
                streak_type=streak_data.get("streak_type", ""),
                streak_count=streak_data.get("current_streak", 0),
                ufc_fight_count=len(fights) if fights else 0,
            )
        except Exception:
            pass

    return profile


def format_tale_of_the_tape(
    profile_a: Dict[str, Any],
    profile_b: Dict[str, Any],
) -> str:
    """
    Format a tale-of-the-tape comparison between two fighter profiles.
    """
    name_a = profile_a.get("name", "Fighter A")
    name_b = profile_b.get("name", "Fighter B")

    lines = [
        f"{'=' * 60}",
        f"  TALE OF THE TAPE: {name_a} vs {name_b}",
        f"{'=' * 60}",
        "",
    ]

    # Physical attributes
    attrs = [
        ("Record", "record"),
        ("Height", "height"),
        ("Reach", "reach"),
        ("Stance", "stance"),
    ]
    for label, key in attrs:
        val_a = profile_a.get(key, "N/A")
        val_b = profile_b.get(key, "N/A")
        lines.append(f"  {val_a:>20}  |  {label:^14}  |  {val_b:<20}")

    lines.append("")

    # Striking stats
    stat_attrs = [
        ("SLpM", "slpm"),
        ("Str. Accuracy", "str_acc"),
        ("SApM", "sapm"),
        ("Str. Defense", "str_def"),
        ("TD Avg", "td_avg"),
        ("TD Accuracy", "td_acc"),
        ("TD Defense", "td_def"),
        ("Sub Avg", "sub_avg"),
    ]
    for label, key in stat_attrs:
        val_a = profile_a.get(key, "—")
        val_b = profile_b.get(key, "—")
        lines.append(f"  {str(val_a):>20}  |  {label:^14}  |  {str(val_b):<20}")

    # Streak and form
    lines.append("")
    streak_a = profile_a.get("streak", {})
    streak_b = profile_b.get("streak", {})
    form_a = streak_a.get("form_last_5", "—")
    form_b = streak_b.get("form_last_5", "—")

    s_a = streak_a.get("current_streak", 0)
    st_a = streak_a.get("streak_type", "")
    s_b = streak_b.get("current_streak", 0)
    st_b = streak_b.get("streak_type", "")

    lines.append(f"  {f'{s_a}{st_a}':>20}  |  {'Streak':^14}  |  {f'{s_b}{st_b}':<20}")
    lines.append(f"  {form_a:>20}  |  {'Form (Last 5)':^14}  |  {form_b:<20}")

    # Method distribution
    md_a = profile_a.get("method_distribution", {})
    md_b = profile_b.get("method_distribution", {})

    if md_a or md_b:
        lines.append("")
        fr_a = f"{md_a.get('finish_rate', 0)}%" if md_a else "—"
        fr_b = f"{md_b.get('finish_rate', 0)}%" if md_b else "—"
        ko_a = f"{md_a.get('ko_rate', 0)}%" if md_a else "—"
        ko_b = f"{md_b.get('ko_rate', 0)}%" if md_b else "—"
        sub_a = f"{md_a.get('sub_rate', 0)}%" if md_a else "—"
        sub_b = f"{md_b.get('sub_rate', 0)}%" if md_b else "—"

        lines.append(f"  {fr_a:>20}  |  {'Finish Rate':^14}  |  {fr_b:<20}")
        lines.append(f"  {ko_a:>20}  |  {'KO Rate':^14}  |  {ko_b:<20}")
        lines.append(f"  {sub_a:>20}  |  {'Sub Rate':^14}  |  {sub_b:<20}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
