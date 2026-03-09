from __future__ import annotations

import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -------------------------------------------------
# Ensure project root is on sys.path
# -------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Import the shared engine entrypoint (async pipeline)
from engine_entry import _run_full_pipeline, clear_task_queue

_logger = logging.getLogger("backend")

app = FastAPI(
    title="UFC Analytics Backend",
    version="2.0.0",
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
