# config.py
# Centralized configuration for the UFC analytics engine.
# All tunable parameters in one place for easy adjustment.

import os
from pathlib import Path

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_DIR = PROJECT_ROOT / "state"
MEMORY_DIR = PROJECT_ROOT / "memory"

# ============================================================
# LLM CONFIGURATION
# ============================================================
# Routing model: fast, cheap, used for routing/specialists/critic
LLM_ROUTING_MODEL = os.getenv("LLM_ROUTING_MODEL", "llama-3.1-8b-instant")
LLM_ROUTING_MAX_TOKENS = int(os.getenv("LLM_ROUTING_MAX_TOKENS", "1536"))
LLM_ROUTING_TEMPERATURE = float(os.getenv("LLM_ROUTING_TEMPERATURE", "0.2"))

# Orchestration model: larger, used for prediction specialist
LLM_ORCHESTRATOR_MODEL = os.getenv("LLM_ORCHESTRATOR_MODEL", "gpt-oss-20b")
LLM_ORCHESTRATOR_MAX_TOKENS = int(os.getenv("LLM_ORCHESTRATOR_MAX_TOKENS", "2048"))
LLM_ORCHESTRATOR_TEMPERATURE = float(os.getenv("LLM_ORCHESTRATOR_TEMPERATURE", "0.3"))

# Concurrency
LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))

# ============================================================
# SPECIALIST CONFIGURATION
# ============================================================
SPECIALIST_TIMEOUT_SECONDS = float(os.getenv("SPECIALIST_TIMEOUT", "60"))
SPECIALIST_MAX_INPUT_TOKENS = int(os.getenv("SPECIALIST_MAX_INPUT_TOKENS", "4500"))
SPECIALIST_TOOL_LOOP_MAX_ITERS = int(os.getenv("SPECIALIST_TOOL_LOOP_ITERS", "4"))

# ============================================================
# TOOL CONFIGURATION
# ============================================================
TOOL_CACHE_TTL_SECONDS = int(os.getenv("TOOL_CACHE_TTL", "300"))  # 5 minutes
TOOL_REQUEST_TIMEOUT = int(os.getenv("TOOL_REQUEST_TIMEOUT", "15"))

# ============================================================
# RETRIEVAL CONFIGURATION
# ============================================================
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_FIGHTER_TOP_K = int(os.getenv("RETRIEVAL_FIGHTER_TOP_K", "3"))

# ============================================================
# MEMORY CONFIGURATION
# ============================================================
MEMORY_LONG_TERM_MAX = int(os.getenv("MEMORY_LONG_TERM_MAX", "500"))
MEMORY_LONG_TERM_DECAY_DAYS = int(os.getenv("MEMORY_LONG_TERM_DECAY_DAYS", "30"))
MEMORY_SHORT_TERM_DECAY_SECONDS = int(os.getenv("MEMORY_SHORT_TERM_DECAY", "86400"))
MEMORY_EPISODIC_RECENT_K = int(os.getenv("MEMORY_EPISODIC_K", "5"))

# ============================================================
# EMBEDDING CONFIGURATION
# ============================================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "2048"))
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))

# ============================================================
# EVENT PIPELINE
# ============================================================
EVENT_PROVIDER_TIMEOUT = float(os.getenv("EVENT_PROVIDER_TIMEOUT", "15"))
