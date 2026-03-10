# tests/test_retrieval_pipeline.py
# Tests for retrieval pipeline with mocked embeddings/vector store.

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestRetrievalPipeline:
    """Tests for get_retrieved_context with mocked embedding + vector store."""

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_empty_input_returns_empty(self, mock_embed, mock_store):
        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("")
        assert result == ""
        mock_embed.assert_not_called()

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_none_input_returns_empty(self, mock_embed, mock_store):
        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context(None)
        assert result == ""

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_basic_query(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1, 0.2, 0.3]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = [
            ({"text": "Pereira has elite power"}, 0.15),
            ({"text": "Ankalaev is a strong wrestler"}, 0.25),
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("Pereira vs Ankalaev")

        assert "Pereira has elite power" in result
        assert "Ankalaev is a strong wrestler" in result
        assert "[score=0.150]" in result

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_deduplicates(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        # Return same text from both query and fighter search
        store_inst.search.return_value = [
            ({"text": "duplicate text"}, 0.1),
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test", fighters=["Fighter A"])

        assert result.count("duplicate text") == 1

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_fighter_metadata_alignment(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst

        # First call: user query (returns nothing)
        # Second call: fighter search (returns entry with wrong metadata)
        store_inst.search.side_effect = [
            [],  # user query
            [
                ({"text": "wrong fighter info", "metadata": {"fighter": "wrong guy"}}, 0.1),
            ],
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test", fighters=["Pereira"])

        # Should be filtered out due to metadata mismatch
        assert "wrong fighter info" not in result

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_fighter_metadata_match(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst

        store_inst.search.side_effect = [
            [],  # user query
            [
                ({"text": "Pereira knockout power", "metadata": {"fighter": "pereira"}}, 0.1),
            ],
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test", fighters=["Pereira"])

        assert "Pereira knockout power" in result

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_sorts_by_score(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = [
            ({"text": "less relevant"}, 0.9),
            ({"text": "most relevant"}, 0.05),
            ({"text": "medium relevant"}, 0.5),
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test query")

        lines = result.strip().split("\n")
        # First line should be the most relevant (lowest score)
        assert "most relevant" in lines[0]
        assert "less relevant" in lines[-1]

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_skips_unknown_fighters(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = []

        from retrieval_pipeline import get_retrieved_context
        # "unknown" should be skipped in fighter search
        result = get_retrieved_context("test", fighters=["unknown", ""])

        # Only the user query search should have been called
        assert store_inst.search.call_count == 1

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_handles_empty_text(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = [
            ({"text": ""}, 0.1),
            ({"text": "   "}, 0.2),
            ({"text": "valid text"}, 0.3),
        ]

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test")

        assert "valid text" in result
        # Empty texts should be filtered out
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 1

    @patch("retrieval_pipeline.VectorStore")
    def test_vector_store_init_failure(self, mock_store_cls):
        mock_store_cls.side_effect = Exception("DB unavailable")

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test query")
        assert result == ""

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_fighter_and_single_fighter_param(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = []

        from retrieval_pipeline import get_retrieved_context
        # Both `fighter` and `fighters` provided, fighter not in fighters list
        result = get_retrieved_context("test", fighter="Solo", fighters=["Other"])

        # Should search for query + Solo + Other = 3 calls
        assert store_inst.search.call_count == 3

    @patch("retrieval_pipeline.VectorStore")
    @patch("retrieval_pipeline.get_embedding")
    def test_fighter_already_in_fighters_list(self, mock_embed, mock_store_cls):
        mock_embed.return_value = [0.1]
        store_inst = MagicMock()
        mock_store_cls.return_value = store_inst
        store_inst.search.return_value = []

        from retrieval_pipeline import get_retrieved_context
        result = get_retrieved_context("test", fighter="Pereira", fighters=["Pereira"])

        # Should not double-search: query + Pereira = 2 calls
        assert store_inst.search.call_count == 2


class TestRetrievalAgent:
    """Tests for retrieval_agent with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_returns_string(self):
        with patch("retrieval_agent.extract_fighters", return_value=(["Pereira", "Ankalaev"], "Pereira")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, return_value=None):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "Pereira vs Ankalaev", [], None, None)
            assert isinstance(result, str)
            assert "Pereira" in result

    @pytest.mark.asyncio
    async def test_includes_query_section(self):
        with patch("retrieval_agent.extract_fighters", return_value=([], "unknown")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, return_value=None):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "test query", [], None, None)
            assert "=== QUERY ===" in result
            assert "test query" in result

    @pytest.mark.asyncio
    async def test_no_fighters_message(self):
        with patch("retrieval_agent.extract_fighters", return_value=([], "unknown")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, return_value=None):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "hello world", [], None, None)
            assert "No clear fighters extracted" in result

    @pytest.mark.asyncio
    async def test_event_context_included(self):
        event = {
            "name": "UFC 316",
            "date": "2025-06-01",
            "location": "Vegas",
            "main_event": {"fighters": ["Islam Makhachev", "Arman Tsarukyan"]},
        }
        with patch("retrieval_agent.extract_fighters", return_value=([], "unknown")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, return_value=event):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "next UFC", [], None, None)
            assert "UFC 316" in result
            assert "Islam Makhachev" in result

    @pytest.mark.asyncio
    async def test_event_context_failure_graceful(self):
        with patch("retrieval_agent.extract_fighters", return_value=(["A", "B"], "A")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, side_effect=Exception("fail")):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "A vs B", [], None, None)
            # Should still return a result despite event context failure
            assert "=== QUERY ===" in result

    @pytest.mark.asyncio
    async def test_ufc_event_regex_fallback(self):
        with patch("retrieval_agent.extract_fighters", return_value=([], "unknown")), \
             patch("retrieval_agent.get_unified_next_event", new_callable=AsyncMock, return_value=None), \
             patch("retrieval_agent.get_event_fighters", return_value=["Pereira", "Ankalaev"]):
            from retrieval_agent import retrieval_agent
            result = await retrieval_agent(None, "who wins ufc 313", [], None, None)
            assert "Pereira" in result
