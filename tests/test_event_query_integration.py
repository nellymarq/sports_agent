# tests/test_event_query_integration.py
# Integration test for event-based queries (e.g., "Who wins UFC 313?")

import os, sys
from unittest.mock import patch, MagicMock
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.mock_llm import MockLLM
from router_agent import router_agent
from supervisor import supervisor_agent
from orchestrator import orchestrator, _resolve_event_id_from_text
from event_utils import get_event_fighters, get_event_by_code
from tools import TOOL_REGISTRY


class TestEventIdResolution:
    def test_resolves_ufc_313(self):
        assert _resolve_event_id_from_text("Who wins UFC 313?") == "ufc_313"

    def test_resolves_ufc_with_space(self):
        assert _resolve_event_id_from_text("UFC 314 main event") == "ufc_314"

    def test_no_event_id(self):
        assert _resolve_event_id_from_text("Who wins Pereira vs Ankalaev?") is None

    def test_resolves_lowercase(self):
        assert _resolve_event_id_from_text("ufc313 predictions") == "ufc_313"


class TestEventFighters:
    def test_next_event_has_fighters(self):
        """Verify the first event in events.json has a main event with fighters."""
        import json
        from pathlib import Path
        events_path = Path(__file__).resolve().parents[1] / "data" / "events.json"
        events = json.loads(events_path.read_text())
        assert len(events) > 0
        first = events[0]
        me = first.get("main_event", {})
        fighters = me.get("fighters", [])
        assert len(fighters) >= 2, f"First event {first.get('id')} has no main event fighters"

    def test_unknown_event(self):
        fighters = get_event_fighters("ufc_999")
        assert fighters == []

    def test_first_event_data_exists(self):
        """Verify events.json has at least one event with valid data."""
        import json
        from pathlib import Path
        events_path = Path(__file__).resolve().parents[1] / "data" / "events.json"
        events = json.loads(events_path.read_text())
        assert len(events) > 0
        first = events[0]
        assert first.get("name"), "First event has no name"


@pytest.mark.asyncio
async def test_event_query_pipeline():
    """Test that 'Who wins UFC 313?' correctly identifies fighters and runs pipeline."""
    llm = MockLLM()
    user_input = "Who wins UFC 313 main event?"

    # Router should detect event_who_wins
    router_output = await router_agent(llm, user_input)
    assert router_output["question_type"] == "event_who_wins"

    # Should select full specialist list for who_wins
    specialists = router_output["specialists"]
    assert len(specialists) >= 4  # at least core four

    # Supervisor builds task plan
    task_plan = await supervisor_agent(
        llm=llm,
        router_output=router_output,
        user_input=user_input,
        history=[],
        retrieved_context="",
    )
    assert len(task_plan["tasks"]) > 0

    # Orchestrator should derive fighters from event data
    with patch("orchestrator.MEMORY_STORE") as mock_mem, \
         patch("orchestrator.store_vectorized_memory"):

        mock_mem.write_short_term = MagicMock()
        mock_mem.write_long_term = MagicMock()
        mock_mem.write_evidence = MagicMock()
        mock_mem.write_specialist_note = MagicMock()
        mock_mem.decay_long_term = MagicMock()
        mock_mem.dedupe_long_term = MagicMock()
        mock_mem.cap_long_term = MagicMock()
        mock_mem.decay_short_term = MagicMock()

        result = await orchestrator(
            llm=llm,
            prediction_llm=llm,
            tool_registry=TOOL_REGISTRY,
            task_plan=task_plan,
            test_mode=False,
        )

        assert isinstance(result, str)
        assert len(result.strip()) > 0
