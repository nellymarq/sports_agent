# cli/update_events.py
# Unified event updater with batch support.
#
# Usage:
#   python -m cli.update_events --event ufc_313           # Single event
#   python -m cli.update_events --all                     # All events
#   python -m cli.update_events --all --legacy            # With legacy export
#   python -m cli.update_events --scheduled               # Only scheduled events

from __future__ import annotations
import argparse
import asyncio
import os
import json
import sys

# Ensure project root is importable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from event_utils import (
    merge_event_data,
    _load_baseline_events,
    _load_event_patches,
)

from data.events_fusion import build_unified_event
from data.fighter_history_service import FighterHistoryService


DATA_DIR = os.path.join(BASE_DIR, "data")
UNIFIED_DIR = os.path.join(DATA_DIR, "unified_events")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UNIFIED_DIR, exist_ok=True)


def _load_all_events():
    """Load all events from events.json."""
    events_path = os.path.join(DATA_DIR, "events.json")
    if not os.path.exists(events_path):
        return []
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("events", [])
    except Exception:
        return []


def _load_legacy_event(event_id: str):
    """Load merged legacy event (baseline + patches)."""
    baseline = _load_baseline_events()
    patches = _load_event_patches()

    by_id = {e.get("id"): e for e in baseline if e.get("id")}
    for p in patches:
        pid = p.get("id")
        if pid and pid in by_id:
            by_id[pid] = merge_event_data(by_id[pid], p)

    return by_id.get(event_id)


async def update_event_async(event_id: str, legacy_seed=None, write_legacy: bool = False):
    """Update a single event asynchronously."""
    _ensure_dirs()

    if legacy_seed is None:
        legacy_seed = _load_legacy_event(event_id)

    if not legacy_seed:
        # Try loading from events.json directly
        for ev in _load_all_events():
            if ev.get("id") == event_id:
                legacy_seed = ev
                break

    if not legacy_seed:
        print(f"  [SKIP] No event data found for id={event_id}")
        return False

    try:
        # Build unified event
        unified = await build_unified_event(event_id, legacy_seed=legacy_seed)

        # Enrich with fighter history
        service = FighterHistoryService()
        enriched = service.enrich_event(unified)

        # Write unified JSON
        out_path = os.path.join(UNIFIED_DIR, f"{event_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enriched.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"  [OK] {event_id} -> {out_path}")

        # Optional: write legacy-compatible export
        if write_legacy:
            legacy_out = os.path.join(UNIFIED_DIR, f"{event_id}_legacy.json")
            with open(legacy_out, "w", encoding="utf-8") as f:
                json.dump(unified.to_legacy_dict(), f, indent=2, ensure_ascii=False)
            print(f"  [OK] Legacy export: {legacy_out}")

        return True
    except Exception as e:
        print(f"  [ERROR] {event_id}: {e}")
        return False


def update_event(event_id: str, write_legacy: bool = False):
    """Sync wrapper for single event update."""
    return asyncio.run(update_event_async(event_id, write_legacy=write_legacy))


async def update_all_events(write_legacy: bool = False, scheduled_only: bool = False):
    """Update all events from events.json."""
    events = _load_all_events()

    if scheduled_only:
        events = [e for e in events if e.get("status") == "scheduled"]

    if not events:
        print("[update-events] No events found.")
        return

    print(f"[update-events] Processing {len(events)} event(s)...")

    success = 0
    for ev in events:
        event_id = ev.get("id")
        if not event_id:
            continue
        result = await update_event_async(event_id, legacy_seed=ev, write_legacy=write_legacy)
        if result:
            success += 1

    print(f"\n[update-events] Done: {success}/{len(events)} events updated successfully.")


def main():
    parser = argparse.ArgumentParser(description="Update unified UFC event data.")
    parser.add_argument("--event", help="Single event ID, e.g. ufc_313")
    parser.add_argument("--all", action="store_true", help="Update all events")
    parser.add_argument("--scheduled", action="store_true", help="Update only scheduled events")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Also write a legacy-compatible export",
    )
    args = parser.parse_args()

    if args.all or args.scheduled:
        asyncio.run(update_all_events(
            write_legacy=args.legacy,
            scheduled_only=args.scheduled,
        ))
    elif args.event:
        update_event(args.event, write_legacy=args.legacy)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
