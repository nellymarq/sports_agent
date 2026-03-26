# data/input_validator.py
# Input validation and sanitization for the UFC analytics engine.
# All functions are pure (no side effects, no I/O).

from __future__ import annotations

import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_INPUT_LENGTH = 1
_MAX_INPUT_LENGTH = 2000
_MIN_FIGHTER_NAME_LENGTH = 2
_MAX_FIGHTER_NAME_LENGTH = 50

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPECIAL_CHARS_RE = re.compile(r"[<>&\";{}()\[\]\\|`~]")  # apostrophes allowed (O'Malley, etc.)
_RECORD_RE = re.compile(r"^(\d{1,3})-(\d{1,3})-(\d{1,3})(?:\s*\(\d+\s*NC\))?$")
_PERCENT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%?$")
_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

# Common UFC fighter name fragments used for detection heuristics
_FIGHTER_INDICATORS = [
    "vs", "versus", "fight", "fighter", "bout",
    "matchup", "match up", "ufc", "mma",
]

_INVALID_NAMES = frozenset({
    "", "unknown", "tbd", "n/a", "none", "null", "undefined",
})

_UFC_KEYWORDS = frozenset({
    "ufc", "mma", "fighter", "fight", "bout", "octagon", "round",
    "knockout", "submission", "decision", "weight class", "ppv",
    "bellator", "ufc stats", "record", "reach", "stance",
    "slpm", "striking", "grappling", "takedown",
})

_GENERIC_SPORT_KEYWORDS = frozenset({
    "nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball",
    "baseball", "hockey", "tennis", "golf", "cricket",
})

_STATS_REQUIRED_KEYS = {"record"}
_STATS_NUMERIC_KEYS = {"slpm", "sapm", "str_acc", "str_def"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_user_input(user_input: str) -> Dict[str, Any]:
    """
    Validate and sanitize user input for the UFC analytics engine.

    Returns:
        {"valid": True, "sanitized": "...", "warnings": []}
        or
        {"valid": False, "error": "...", "suggestions": []}
    """
    warnings: List[str] = []
    suggestions: List[str] = []

    # --- type check ---
    if not isinstance(user_input, str):
        return {
            "valid": False,
            "error": "Input must be a string.",
            "suggestions": ["Please provide your question as text."],
        }

    # --- length checks (before sanitization) ---
    if len(user_input.strip()) < _MIN_INPUT_LENGTH:
        return {
            "valid": False,
            "error": "Input is empty.",
            "suggestions": [
                "Ask a UFC-related question, e.g. "
                "'Who wins: Khabib vs McGregor?'",
            ],
        }

    if len(user_input) > _MAX_INPUT_LENGTH:
        return {
            "valid": False,
            "error": f"Input is too long ({len(user_input)} chars). "
                     f"Maximum is {_MAX_INPUT_LENGTH} characters.",
            "suggestions": ["Please shorten your question."],
        }

    # --- sanitize ---
    sanitized = _sanitize_text(user_input)

    if len(sanitized.strip()) < _MIN_INPUT_LENGTH:
        return {
            "valid": False,
            "error": "Input contains no usable text after sanitization.",
            "suggestions": ["Please rephrase without HTML tags or special characters."],
        }

    # --- fighter name detection ---
    lower = sanitized.lower()
    has_fighter_indicator = any(kw in lower for kw in _FIGHTER_INDICATORS)
    if not has_fighter_indicator:
        warnings.append(
            "No fighter names or fight-related terms detected. "
            "Results may be limited."
        )

    # --- question clarity ---
    word_count = len(sanitized.split())
    if word_count < 3:
        warnings.append(
            "Very short input — consider adding more detail for better analysis."
        )

    # --- UFC context ---
    has_ufc_keyword = any(kw in lower for kw in _UFC_KEYWORDS)
    has_generic_sport = any(kw in lower for kw in _GENERIC_SPORT_KEYWORDS)

    if has_generic_sport and not has_ufc_keyword:
        warnings.append(
            "This appears to be about a non-UFC sport. "
            "This engine specializes in UFC/MMA analytics."
        )
        suggestions.append(
            "Try rephrasing with UFC-specific terms, e.g. "
            "'Compare UFC fighter X vs Y'."
        )

    result: Dict[str, Any] = {
        "valid": True,
        "sanitized": sanitized,
        "warnings": warnings,
    }
    if suggestions:
        result["suggestions"] = suggestions
    return result


def validate_fighter_name(name: str) -> Dict[str, Any]:
    """
    Validate a fighter name for API lookups.

    Returns:
        {"valid": True, "sanitized": "..."}
        or
        {"valid": False, "error": "..."}
    """
    if not isinstance(name, str):
        return {"valid": False, "error": "Fighter name must be a string."}

    cleaned = name.strip()

    if cleaned.lower() in _INVALID_NAMES:
        return {"valid": False, "error": f"Invalid fighter name: '{cleaned}'."}

    if len(cleaned) < _MIN_FIGHTER_NAME_LENGTH:
        return {
            "valid": False,
            "error": f"Fighter name too short ({len(cleaned)} chars). "
                     f"Minimum is {_MIN_FIGHTER_NAME_LENGTH}.",
        }

    if len(cleaned) > _MAX_FIGHTER_NAME_LENGTH:
        return {
            "valid": False,
            "error": f"Fighter name too long ({len(cleaned)} chars). "
                     f"Maximum is {_MAX_FIGHTER_NAME_LENGTH}.",
        }

    # Reject names with special chars that could break HTML parsing
    if _SPECIAL_CHARS_RE.search(cleaned):
        return {
            "valid": False,
            "error": "Fighter name contains invalid special characters.",
        }

    # Strip HTML / control chars
    sanitized = _sanitize_text(cleaned)
    if len(sanitized.strip()) < _MIN_FIGHTER_NAME_LENGTH:
        return {
            "valid": False,
            "error": "Fighter name is empty after sanitization.",
        }

    return {"valid": True, "sanitized": sanitized}


def validate_stats_response(
    stats: Dict[str, Any],
    fighter_name: str,
) -> Dict[str, Any]:
    """
    Validate fighter stats returned by the UFCStats tool.

    Returns:
        {
            "valid": True/False,
            "warnings": [...],
            "data_quality_score": 0.0-1.0,
            "error": "..." (only when valid=False)
        }
    """
    warnings: List[str] = []

    if not isinstance(stats, dict):
        return {
            "valid": False,
            "error": "Stats response is not a dictionary.",
            "warnings": [],
            "data_quality_score": 0.0,
        }

    if not stats:
        return {
            "valid": False,
            "error": f"Empty stats response for '{fighter_name}'.",
            "warnings": [],
            "data_quality_score": 0.0,
        }

    # --- required keys (must exist AND have non-empty value) ---
    missing = set()
    for key in _STATS_REQUIRED_KEYS:
        if key not in stats or not stats[key]:
            missing.add(key)
    if missing:
        return {
            "valid": False,
            "error": f"Missing required stat keys for '{fighter_name}': "
                     f"{', '.join(sorted(missing))}.",
            "warnings": [],
            "data_quality_score": 0.0,
        }

    score_parts: List[float] = []

    # --- record format ---
    record = stats.get("record", "")
    if record:
        record_match = _RECORD_RE.match(str(record).strip())
        if record_match:
            score_parts.append(1.0)
            wins = int(record_match.group(1))
            losses = int(record_match.group(2))
            total = wins + losses
            if total > 80:
                warnings.append(
                    f"Unusually high total fights ({total}) for '{fighter_name}'. "
                    "Data may be stale or incorrect."
                )
        else:
            warnings.append(
                f"Record '{record}' for '{fighter_name}' does not match "
                "expected W-L-D format."
            )
            score_parts.append(0.0)
    else:
        score_parts.append(0.0)
        warnings.append(f"Record is empty for '{fighter_name}'.")

    # --- numeric stat fields ---
    for key in sorted(_STATS_NUMERIC_KEYS):
        val = stats.get(key, "")
        if val == "" or val is None:
            score_parts.append(0.0)
            warnings.append(f"'{key}' is missing for '{fighter_name}'.")
            continue
        val_str = str(val).replace("%", "").strip()
        if _NUMERIC_RE.match(val_str):
            score_parts.append(1.0)
        else:
            score_parts.append(0.0)
            warnings.append(
                f"'{key}' value '{val}' for '{fighter_name}' is not a valid number."
            )

    # --- age ---
    age = stats.get("age")
    if age is not None:
        try:
            age_num = int(age)
            if 18 <= age_num <= 55:
                score_parts.append(1.0)
            else:
                score_parts.append(0.3)
                warnings.append(
                    f"Age {age_num} for '{fighter_name}' is outside "
                    "expected range (18-55)."
                )
        except (ValueError, TypeError):
            score_parts.append(0.0)
            warnings.append(
                f"Age value '{age}' for '{fighter_name}' is not a valid integer."
            )

    # --- reach ---
    reach = stats.get("reach")
    if reach is not None and str(reach).strip():
        reach_str = str(reach).replace('"', "").replace("in", "").strip()
        reach_match = _NUMERIC_RE.match(reach_str)
        if reach_match:
            reach_val = float(reach_str)
            if 60 <= reach_val <= 85:
                score_parts.append(1.0)
            else:
                score_parts.append(0.3)
                warnings.append(
                    f"Reach {reach_val}\" for '{fighter_name}' is outside "
                    "expected range (60-85 inches)."
                )
        else:
            # Reach may be a descriptive string like "72.0\"" — don't penalize heavily
            score_parts.append(0.5)
            warnings.append(
                f"Reach value '{reach}' for '{fighter_name}' could not be parsed."
            )

    # --- data quality score ---
    if score_parts:
        data_quality_score = round(sum(score_parts) / len(score_parts), 2)
    else:
        data_quality_score = 0.0

    if data_quality_score < 0.5:
        warnings.append(
            f"Low data quality score ({data_quality_score}) for '{fighter_name}'. "
            "Analysis may be unreliable."
        )

    return {
        "valid": True,
        "warnings": warnings,
        "data_quality_score": data_quality_score,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitize_text(text: str) -> str:
    """Strip HTML tags and control characters, collapse whitespace."""
    result = _HTML_TAG_RE.sub("", text)
    result = _CONTROL_CHAR_RE.sub("", result)
    # Collapse runs of whitespace into single spaces
    result = re.sub(r"\s+", " ", result).strip()
    return result
