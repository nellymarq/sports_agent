#!/bin/bash

# ============================================================
# SPORTS AGENT AUTONOMOUS LOOP
# Run: chmod +x agent-loop.sh && ./agent-loop.sh
# Stop: Ctrl+C
# ============================================================

PROJECT_DIR="${1:-$(pwd)}"
LOG_FILE="$PROJECT_DIR/claude-loop.log"
ITERATION=0

cd "$PROJECT_DIR" || { echo "ERROR: Cannot find project directory: $PROJECT_DIR"; exit 1; }

# Allow nested Claude Code invocation
unset CLAUDECODE

echo "Autonomous loop started at $(date)" | tee -a "$LOG_FILE"
echo "Project dir: $PROJECT_DIR" | tee -a "$LOG_FILE"

PROMPT='Work autonomously on this UFC multi-agent prediction system and try to never run out of things to improve. Use looping/self-continuation strategies if needed. Do NOT ask any questions — make all decisions using your best judgment and industry research.

RESEARCH DIRECTIVE:
Continuously research how top sports analytics platforms (ESPN Analytics, FightMetric, Verdicts MMA, Tapology, BetMMA, Sherdog, Action Network, The Athletic, DecisionBot, etc.) implement features — and improve this system to match or surpass them. Focus on prediction accuracy, data quality, UX, performance, and features relevant to serious MMA/UFC analysts and bettors.

PROJECT OVERVIEW:
- Multi-agent UFC prediction system with 14+ specialists (style, form, grappling, damage, pace, fight_iq, scramble, gameplan, judging, sentiment, weightcut, metadata, knowledge)
- DAG-based orchestrator: specialists (parallel) → coordinator → prediction → critic
- Groq LLM API (llama-3.1-8b-instant for routing, gpt-oss-20b for prediction)
- Real data tools: UFCStats HTML parsing, ESPN API, DraftKings odds, Polymarket
- Three-tier memory: semantic, episodic, vectorized (sentence-transformers)
- FastAPI backend + Next.js frontend + Docker Compose
- Prediction tracking with calibration (Brier score, accuracy by tier)
- SSE streaming for real-time pipeline progress
- Token-bucket rate limiting for Groq API

KEY AREAS TO IMPROVE:
- Prediction accuracy and specialist output quality
- Frontend UX (visualizations, fight cards, comparison views)
- Data enrichment (more providers, historical fight data, training camp intel)
- Performance optimization (caching, parallel execution, latency reduction)
- Test coverage and reliability
- Fighter database and historical record tracking
- Odds analysis and value bet identification
- Event coverage automation (auto-ingest upcoming cards)

WORKFLOW RULES:
- Commit after each logical chunk of work with descriptive commit messages
- Do NOT push until the very end — single push to origin/main at end of session
- Run tests with: .venv/bin/python -m pytest -q (NOT system python)
- Do not break existing tests (run full suite periodically)
- Keep commits atomic and well-described
- Use existing patterns — do not over-engineer or add unnecessary abstractions
- Mock external services in tests — never call real APIs in test suite
- Research before implementing any major feature
- Git remote: origin https://github.com/nellymarq/sports_agent.git, branch: main

LOOP RULE (CRITICAL):
When you are nearing the end of your context or have completed a major chunk of work:
1. Write a TASKS.md update summarizing what was completed and what remains
2. Regenerate a refreshed version of this full prompt incorporating current project state
3. Output the refreshed prompt as the last thing you do so the loop script can re-invoke you automatically

Keep improving the sports agent indefinitely until the loop is manually stopped.'

while true; do
  ITERATION=$((ITERATION + 1))
  echo "" | tee -a "$LOG_FILE"
  echo "=====================================================" | tee -a "$LOG_FILE"
  echo "ITERATION $ITERATION — $(date)" | tee -a "$LOG_FILE"
  echo "=====================================================" | tee -a "$LOG_FILE"

  # If TASKS.md exists, append current state to prompt
  if [ -f "$PROJECT_DIR/TASKS.md" ]; then
    FULL_PROMPT="$PROMPT

CURRENT TASK STATE (from TASKS.md):
$(cat "$PROJECT_DIR/TASKS.md")"
  else
    FULL_PROMPT="$PROMPT"
  fi

  claude --dangerously-skip-permissions -p "$FULL_PROMPT" 2>&1 | tee -a "$LOG_FILE"

  EXIT_CODE=${PIPESTATUS[0]}

  echo "" | tee -a "$LOG_FILE"
  echo "Iteration $ITERATION complete (exit code: $EXIT_CODE) — $(date)" | tee -a "$LOG_FILE"

  if [ $EXIT_CODE -ne 0 ]; then
    echo "Non-zero exit. Retrying in 10 seconds..." | tee -a "$LOG_FILE"
    sleep 10
  else
    sleep 3
  fi
done
