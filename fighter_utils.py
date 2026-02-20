# fighter_utils.py
# Simple fighter name extraction

import re


def extract_fighter_name(text: str) -> str:
    """
    Naive but effective: first capitalized word pair.
    Falls back to 'unknown' if nothing found.
    """
    match = re.search(r"\b([A-Z][a-z]+)\s([A-Z][a-z]+)\b", text)
    return match.group(0) if match else "unknown"
