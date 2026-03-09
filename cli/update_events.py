# cli/update_events.py
# Unified event updater (Option A: additive, non-breaking)
#
# - Loads legacy baseline + patches
# - Builds unified event via fusion layer
# - Enriches with fighter history
# - Writes unified JSON to data/unified_events/<event_id>.json
# - Optionally writes legacy-compatible export

from __future__ import annotations
import argparse
import os
import json

from event_utils import (
    get_event_by_code,
    merge_event_data,
    _load_baseline_events,
    _load_event_patches,
)

from data.events_fusion import build_unified_event
from data.fighter_history_service import FighterHistoryService


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UNIFIED_DIR = os.path.join(DATA_DIR, "unified_events")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UNIFIED_DIR, exist_ok=True)


def _load_legacy_event(event_id: str):
    """
    Load merged legacy event (baseline + patches).
    """
    baseline = _load_baseline_events()
    patches = _load_event_patches()

    by_id = {e.get("id"): e for e in baseline if e.get("id")}
    for p in patches:
        pid = p.get("id")
        if pid and pid in by_id:
            by_id[pid] = merge_event_data(by_id[pid], p)

    return by_id.get(event_id)


def update_event(event_id: str, write_legacy: bool = False):
    _ensure_dirs()

    legacy = _load_legacy_event(event_id)
    if not legacy:
        print(f"[update-events] No legacy event found for id={event_id}")
        return

    # Build unified event
    unified = build_unified_event(event_id, legacy_seed=legacy)

    # Enrich with fighter history
    service = FighterHistoryService()
    enriched = service.enrich_event(unified)

    # Write unified JSON
    out_path = os.path.join(UNIFIED_DIR, f"{event_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(enriched.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"[update-events] Unified event written: {out_path}")

    # Optional: write legacy-compatible export
    if write_legacy:
        legacy_out = os.path.join(UNIFIED_DIR, f"{event_id}_legacy.json")
        with open(legacy_out, "w", encoding="utf-8") as f:
            json.dump(unified.to_legacy_dict(), f, indent=2, ensure_ascii=False)
        print(f"[update-events] Legacy export written: {legacy_out}")


def main():
    parser = argparse.ArgumentParser(description="Update unified UFC event data.")
    parser.add_argument("--event", required=True, help="Event ID, e.g. ufc_313")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Also write a legacy-compatible export",
    )
    args = parser.parse_args()

    update_event(args.event, write_legacy=args.legacy)


if __name__ == "__main__":
    main()
