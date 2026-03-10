from __future__ import annotations

import asyncio
import json
import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# -------------------------------------------------
# Ensure project root is on sys.path
# -------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Import the shared engine entrypoint (async pipeline)
from engine_entry import _run_full_pipeline, clear_task_queue, LLM_ROUTING, LLM_ORCHESTRATOR, get_pipeline_timings
from prediction_tracker import get_calibration_stats, record_result, _load_predictions
from config import validate_config
from data.providers.odds_provider import fetch_all_ufc_odds
from data.value_bets import (
    identify_value_bets,
    format_value_bet_report,
    american_to_implied,
    decimal_to_implied,
    implied_to_american,
    remove_vig,
)
from tools import UFCStatsTool
from tools.comparison import build_comparison
from data.events_schema import Event
from cache.cache_manager import CacheManager

_logger = logging.getLogger("backend")

# Shared cache instance
_cache = CacheManager()

# -------------------------------------------------
# Startup validation
# -------------------------------------------------
_config_errors = validate_config()
if _config_errors:
    for err in _config_errors:
        _logger.warning(f"CONFIG WARNING: {err}")

app = FastAPI(
    title="UFC Analytics Backend",
    version="2.3.0",
)

# -------------------------------------------------
# CORS (allow frontend on port 3000)
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# Request/Response Models
# -------------------------------------------------
class AnalyzeRequest(BaseModel):
    user_input: str


class AnalyzeResponse(BaseModel):
    content: str
    elapsed_seconds: Optional[float] = None


class RecordResultRequest(BaseModel):
    event_id: str
    fighter_a: str
    fighter_b: str
    actual_winner: str
    actual_method: str = ""


class CompareRequest(BaseModel):
    fighter_a: str
    fighter_b: str


class ValueBetRequest(BaseModel):
    min_edge: float = 0.03
    bankroll: float = 1000
    kelly_fraction: float = 0.25


class FighterSearchRequest(BaseModel):
    query: str


# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": app.version,
        "models": {
            "routing": LLM_ROUTING.model,
            "prediction": LLM_ORCHESTRATOR.model,
        },
    }


@app.get("/stats")
def stats() -> Dict[str, Any]:
    """Return LLM usage stats and pipeline timings for monitoring."""
    timings = get_pipeline_timings()
    return {
        "routing_llm": LLM_ROUTING.stats,
        "prediction_llm": LLM_ORCHESTRATOR.stats,
        "recent_pipelines": len(timings),
        "pipeline_timings": timings[-5:] if timings else [],
    }


# -------------------------------------------------
# Main Analysis Endpoint (ASYNC)
# -------------------------------------------------
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Runs the full multi-agent UFC pipeline:
    retrieval → router → supervisor → orchestrator → critic.
    """
    t0 = time.monotonic()
    try:
        clear_task_queue()
        result = await _run_full_pipeline(req.user_input)
        elapsed = round(time.monotonic() - t0, 2)
        _logger.info(f"Analysis completed in {elapsed}s for: {req.user_input[:80]}")
        return AnalyzeResponse(content=result, elapsed_seconds=elapsed)

    except Exception as e:
        _logger.exception(f"Analysis failed for: {req.user_input[:80]}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Streaming Analysis Endpoint (SSE)
# -------------------------------------------------
@app.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest) -> StreamingResponse:
    """
    Server-Sent Events endpoint that streams pipeline stage updates,
    then the final analysis content.
    """

    async def event_generator():
        t0 = time.monotonic()
        stage_queue: asyncio.Queue[str] = asyncio.Queue()

        def on_stage(stage_name: str):
            stage_queue.put_nowait(stage_name)

        # Start the pipeline in a background task
        clear_task_queue()
        pipeline_task = asyncio.create_task(
            _run_full_pipeline(req.user_input, on_stage=on_stage)
        )

        # Yield stage events as they arrive
        while not pipeline_task.done():
            try:
                stage = await asyncio.wait_for(stage_queue.get(), timeout=1.0)
                yield f"data: {json.dumps({'type': 'stage', 'stage': stage})}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive comment
                yield ": keepalive\n\n"

        # Drain remaining stages
        while not stage_queue.empty():
            stage = stage_queue.get_nowait()
            yield f"data: {json.dumps({'type': 'stage', 'stage': stage})}\n\n"

        # Get result or error
        try:
            result = await pipeline_task
            elapsed = round(time.monotonic() - t0, 2)
            yield f"data: {json.dumps({'type': 'result', 'content': result, 'elapsed_seconds': elapsed})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -------------------------------------------------
# Prediction Calibration Endpoints
# -------------------------------------------------
@app.get("/calibration")
def calibration() -> Dict[str, Any]:
    """Return prediction calibration stats."""
    return get_calibration_stats()


@app.post("/result")
def submit_result(req: RecordResultRequest) -> Dict[str, Any]:
    """Record an actual fight result for calibration tracking."""
    updated = record_result(
        event_id=req.event_id,
        fighter_a=req.fighter_a,
        fighter_b=req.fighter_b,
        actual_winner=req.actual_winner,
        actual_method=req.actual_method,
    )
    if updated:
        return {"status": "ok", "prediction": updated}
    return {"status": "not_found", "message": "No matching prediction found."}


# -------------------------------------------------
# Live Odds Endpoint
# -------------------------------------------------
@app.get("/odds")
def get_odds() -> Dict[str, Any]:
    """Fetch live UFC odds from all available providers."""
    try:
        odds = fetch_all_ufc_odds()
        bout_count = len(odds.get("bouts", {}))
        return {
            "status": "ok",
            "bout_count": bout_count,
            "odds": odds,
        }
    except Exception as e:
        _logger.exception("Failed to fetch odds")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Value Bet Identification Endpoint
# -------------------------------------------------
@app.post("/value-bets")
def get_value_bets(req: ValueBetRequest) -> Dict[str, Any]:
    """
    Identify value bets by comparing stored predictions against live market odds.
    Requires existing predictions in the tracker.
    """
    try:
        predictions = _load_predictions()
        # Filter to unresolved predictions only
        active = [
            p for p in predictions
            if p.get("actual_winner") is None and p.get("win_probability", 0) > 0
        ]

        if not active:
            return {
                "status": "ok",
                "value_bets": [],
                "message": "No active predictions to compare against odds.",
            }

        odds = fetch_all_ufc_odds()
        value_bets = identify_value_bets(
            predictions=active,
            odds_data=odds,
            min_edge=req.min_edge,
            bankroll=req.bankroll,
            kelly_fraction_pct=req.kelly_fraction,
        )

        return {
            "status": "ok",
            "active_predictions": len(active),
            "odds_bouts": len(odds.get("bouts", {})),
            "value_bets": value_bets,
            "report": format_value_bet_report(value_bets),
        }
    except Exception as e:
        _logger.exception("Failed to identify value bets")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Fighter Comparison Endpoint
# -------------------------------------------------
_ufc_stats_tool = UFCStatsTool()


@app.post("/compare")
def compare_fighters(req: CompareRequest) -> Dict[str, Any]:
    """
    Head-to-head fighter comparison using live UFCStats data.
    Returns structured comparison with statistical edges.
    """
    try:
        data_a = _ufc_stats_tool.invoke({"fighter_name": req.fighter_a})
        data_b = _ufc_stats_tool.invoke({"fighter_name": req.fighter_b})

        if data_a.get("error"):
            raise HTTPException(status_code=404, detail=f"Fighter not found: {req.fighter_a}")
        if data_b.get("error"):
            raise HTTPException(status_code=404, detail=f"Fighter not found: {req.fighter_b}")

        fighter_a = data_a.get("best_match", {})
        fighter_b = data_b.get("best_match", {})

        comparison_text = build_comparison(fighter_a, fighter_b)

        return {
            "status": "ok",
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "comparison": comparison_text,
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.exception("Fighter comparison failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Odds Converter Utility Endpoint
# -------------------------------------------------
@app.get("/odds/convert")
def convert_odds(american: Optional[str] = None, decimal: Optional[float] = None) -> Dict[str, Any]:
    """Convert between odds formats (American <-> Decimal <-> Implied)."""
    if american:
        implied = american_to_implied(american)
        if implied is None:
            raise HTTPException(status_code=400, detail=f"Invalid American odds: {american}")
        dec = round(1.0 / implied, 4) if implied > 0 else None
        return {
            "american": american,
            "decimal": dec,
            "implied_probability": implied,
            "implied_pct": f"{implied * 100:.1f}%",
        }
    elif decimal is not None:
        implied = decimal_to_implied(decimal)
        if implied is None:
            raise HTTPException(status_code=400, detail=f"Invalid decimal odds: {decimal}")
        am = implied_to_american(implied)
        return {
            "american": am,
            "decimal": decimal,
            "implied_probability": implied,
            "implied_pct": f"{implied * 100:.1f}%",
        }
    else:
        raise HTTPException(status_code=400, detail="Provide either 'american' or 'decimal' query parameter.")


# -------------------------------------------------
# Prediction History Endpoint
# -------------------------------------------------
@app.get("/predictions")
def list_predictions(
    event_id: Optional[str] = None,
    resolved_only: bool = False,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Browse prediction history with optional filtering.
    Useful for reviewing past predictions and tracking performance over time.
    """
    preds = _load_predictions()

    if event_id:
        preds = [p for p in preds if p.get("event_id") == event_id]

    if resolved_only:
        preds = [p for p in preds if p.get("correct") is not None]

    # Sort by timestamp descending (most recent first)
    preds.sort(key=lambda p: p.get("timestamp", 0), reverse=True)

    # Apply limit
    preds = preds[:limit]

    return {
        "status": "ok",
        "count": len(preds),
        "predictions": preds,
    }


# -------------------------------------------------
# Upcoming Events Endpoint
# -------------------------------------------------
@app.get("/events")
def list_events() -> Dict[str, Any]:
    """
    Return all known events from the events data store.
    Includes fight cards with fighter details.
    """
    import json
    from pathlib import Path

    events_path = ROOT / "data" / "events.json"
    if not events_path.exists():
        return {"status": "ok", "events": [], "message": "No events data found."}

    try:
        raw = json.loads(events_path.read_text(encoding="utf-8"))
        events_list = raw if isinstance(raw, list) else raw.get("events", [])

        # Enrich each event with structured card data
        enriched = []
        for ev_data in events_list:
            event = Event.from_legacy_dict(ev_data)
            ev_dict = event.to_dict()
            # Add a summary for quick display
            main_fighters = []
            if event.main_event and event.main_event.fighters:
                main_fighters = [f.name for f in event.main_event.fighters]
            ev_dict["main_event_display"] = " vs ".join(main_fighters) if main_fighters else "TBA"
            ev_dict["bout_count"] = len(event.card) + (1 if event.main_event else 0) + (1 if event.co_main_event else 0)
            enriched.append(ev_dict)

        return {
            "status": "ok",
            "count": len(enriched),
            "events": enriched,
        }
    except Exception as e:
        _logger.exception("Failed to load events")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Single Event Card Endpoint
# -------------------------------------------------
@app.get("/events/{event_id}")
def get_event(event_id: str) -> Dict[str, Any]:
    """
    Return detailed card data for a specific event.
    Includes all bouts, fighters, and available odds.
    """
    import json
    from pathlib import Path

    events_path = ROOT / "data" / "events.json"
    if not events_path.exists():
        raise HTTPException(status_code=404, detail="Events data not found.")

    try:
        raw = json.loads(events_path.read_text(encoding="utf-8"))
        events_list = raw if isinstance(raw, list) else raw.get("events", [])

        for ev_data in events_list:
            if ev_data.get("id") == event_id:
                event = Event.from_legacy_dict(ev_data)
                ev_dict = event.to_dict()

                # Add display helpers
                main_fighters = []
                if event.main_event and event.main_event.fighters:
                    main_fighters = [f.name for f in event.main_event.fighters]
                ev_dict["main_event_display"] = " vs ".join(main_fighters) if main_fighters else "TBA"

                # Count total bouts
                ev_dict["bout_count"] = len(event.card) + (1 if event.main_event else 0) + (1 if event.co_main_event else 0)

                # Check for existing predictions for this event
                event_preds = [p for p in _load_predictions() if p.get("event_id") == event_id]
                ev_dict["prediction_count"] = len(event_preds)

                return {"status": "ok", "event": ev_dict}

        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    except HTTPException:
        raise
    except Exception as e:
        _logger.exception("Failed to load event")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Fighter Search Endpoint
# -------------------------------------------------
@app.post("/fighters/search")
def search_fighters(req: FighterSearchRequest) -> Dict[str, Any]:
    """
    Search for a fighter by name using UFCStats data.
    Returns structured fighter data including stats and recent fights.
    """
    try:
        data = _ufc_stats_tool.invoke({"fighter_name": req.query})
        if data.get("error"):
            return {
                "status": "ok",
                "results": [],
                "message": f"No fighters found matching '{req.query}'",
            }

        fighter = data.get("best_match", {})
        return {
            "status": "ok",
            "results": [fighter] if fighter else [],
            "query": req.query,
        }
    except Exception as e:
        _logger.exception("Fighter search failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# Cache Management Endpoints
# -------------------------------------------------
@app.get("/cache/stats")
def cache_stats() -> Dict[str, Any]:
    """Return cache statistics."""
    return _cache.stats()


@app.post("/cache/cleanup")
def cache_cleanup() -> Dict[str, Any]:
    """Remove expired cache entries."""
    removed = _cache.cleanup_expired()
    return {"status": "ok", "removed": removed, **_cache.stats()}
