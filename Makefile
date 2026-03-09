# =====================================================================
#  AUTO-LOAD .env VARIABLES
# =====================================================================
.PHONY: doctor health tree imports test integration agent app specialists update event-history backend frontend dev shell clean install help
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif

# =====================================================================
#  PYTHON SETTINGS
# =====================================================================
PYTHON := python3
PIP := .venv/bin/pip

# =====================================================================
#  DEVTOOLS COMMANDS
# =====================================================================
doctor:
	$(PYTHON) devtools/project_doctor.py

health:
	$(PYTHON) devtools/health_check.py

tree:
	$(PYTHON) devtools/check_tree.py

imports:
	$(PYTHON) devtools/validate_imports.py

# =====================================================================
#  TEST SUITE (pytest)
# =====================================================================
test:
	pytest -q

integration:
	pytest tests/test_full_integration.py -vv

# =====================================================================
#  CORE COMMANDS
# =====================================================================
agent:
	$(PYTHON) agent.py

specialists:
	$(PYTHON) scripts/generate_specialists.py

update:
	$(PYTHON) -m cli.update_events --event $(EVENT)

event-history:
	$(PYTHON) cli/init_history_db.py

# =====================================================================
#  FRONTEND / BACKEND
# =====================================================================
backend:
	cd backend && ../.venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	make -j2 backend frontend

# =====================================================================
#  ENVIRONMENT / CLEANUP / UTILITY
# =====================================================================
shell:
	bash -c "source .venv/bin/activate && bash"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f .pytest_cache
	rm -f */*.pyc
	rm -f *.pyc

install:
	$(PIP) install -r requirements.lock

# =====================================================================
#  HELP
# =====================================================================
help:
	@echo ""
	@echo "Available commands:"
	@echo "  make app                - Run Streamlit app"
	@echo "  make backend            - Run FastAPI backend"
	@echo "  make frontend           - Run Next.js frontend"
	@echo "  make dev                - Run backend + frontend together"
	@echo "  make update EVENT=ufc_313 - Update event data"
	@echo "  make specialists        - Regenerate specialists"
	@echo "  make test               - Run test suite"
	@echo "  make integration        - Run full integration test"
	@echo "  make clean              - Remove caches"
	@echo "  make install            - Install dependencies"
	@echo "  make shell              - Open shell with venv"
	@echo ""
