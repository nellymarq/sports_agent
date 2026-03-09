from __future__ import annotations

import asyncio
import json
import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

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
from engine_entry import _run_full_pipeline, clear_task_queue
from prediction_tracker import get_calibration_stats, record_result

_logger = logging.getLogger("backend")

app = FastAPI(
    title="UFC Analytics Backend",
    version="2.1.0",
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


# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


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
