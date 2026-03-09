from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

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

app = FastAPI(
    title="UFC Analytics Backend",
    version="1.0.0",
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
    This version is async-safe and avoids asyncio.run(),
    preventing Groq semaphore event-loop conflicts.
    """
    try:
        clear_task_queue()
        result = await _run_full_pipeline(req.user_input)
        return AnalyzeResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
