# =====================================================================
#  AUTO-LOAD .env VARIABLES
# =====================================================================
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif

# =====================================================================
#  PYTHON SETTINGS
# =====================================================================
PYTHON := python3

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
#  APP / AGENT RUNNERS
# =====================================================================
agent:
	$(PYTHON) agent.py

app:
	streamlit run app.py

# =====================================================================
#  CLEANUP
# =====================================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
